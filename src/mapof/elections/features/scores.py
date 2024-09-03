#!/usr/bin/env python

import math
import os
import sys

from mapof.elections.other.glossary import LIST_OF_FAKE_MODELS

import numpy as np
try:
    import pulp
except Exception:
    pulp = None

try:
    from dotenv import load_dotenv
    load_dotenv()
    sys.path.append(os.environ["PATH"])
    from abcvoting import abcrules, preferences
except ImportError:
    abcrules = None
    preferences = None

from mapof.elections.distances import ilp_other
from mapof.elections.other import winners as win


# MAIN FUNCTIONS
def highest_borda_score(election) -> dict:
    """
    Computes the highest Borda score of a given election.

    Parameters
    ----------
        election : OrdinalElection

    Returns
    -------
        dict
            'value': highest Borda score
    """
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None}
    n = election.num_voters
    m = election.num_candidates
    vectors = election.get_vectors()
    scores = [0 for _ in range(m)]

    for i in range(n):
        for j in range(m):
            scores[vectors[i][j]] += m - j - 1

    return {'value': max(scores) * election.num_voters}


def highest_plurality_score(election) -> dict:
    """
    Computes the highest Plurality score of a given election.

    Parameters
    ----------
        election : OrdinalElection

    Returns
    -------
        dict
            'value': highest Plurality score
    """
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None}
    first_pos = election.get_matrix()[0]
    return {'value': max(first_pos) * election.num_voters}


def highest_copeland_score(election) -> dict:
    """
    Computes the highest Copeland score of a given election.

    Parameters
    ----------
        election : OrdinalElection

    Returns
    -------
        dict
            'value': highest Copeland score

    """
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None}

    election.compute_potes()
    scores = np.zeros([election.num_candidates])

    for i in range(election.num_candidates):
        for j in range(i + 1, election.num_candidates):
            result = 0
            for k in range(election.num_voters):
                if election.potes[k][i] < election.potes[k][j]:
                    result += 1
            if result > election.num_voters / 2:
                scores[i] += 1
            elif result < election.num_voters / 2:
                scores[j] += 1
            else:
                scores[i] += 0.5
                scores[j] += 0.5

    return {'value': max(scores)}


def lowest_dodgson_score(election):
    """
    Computes the lowest Dodgson score of a given election

    Parameters
    ----------
        election : OrdinalElection

    Returns
    -------
        dict
            'value': lowest Dodgson score
    """
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None}

    min_score = math.inf

    for target_id in range(election.num_candidates):

        # PREPARE N
        unique_potes, N = _potes_to_unique_potes(election.get_potes())

        e = np.zeros([len(N), election.num_candidates,
                      election.num_candidates])

        # PREPARE e
        for i, p in enumerate(unique_potes):
            for j in range(election.num_candidates):
                for k in range(election.num_candidates):
                    if p[target_id] <= p[k] + j:
                        e[i][j][k] = 1

        # PREPARE D
        D = [0 for _ in range(election.num_candidates)]
        threshold = math.ceil((election.num_voters + 1) / 2.)
        for k in range(election.num_candidates):
            diff = 0
            for i, p in enumerate(unique_potes):
                if p[target_id] < p[k]:
                    diff += N[i]
                if diff >= threshold:
                    D[k] = 0
                else:
                    D[k] = threshold - diff
        D[target_id] = 0  # always winning

        score = ilp_other.solve_lp_file_dodgson_score(N=N, e=e, D=D)

        if score < min_score:
            min_score = score

    return min_score


def highest_cc_score(election, committee_size=1):
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None, 'dissat': None}
    winners, total_time = win.generate_winners(election=election,
                                             num_winners=committee_size,
                                             ballot="ordinal",
                                             type='borda_owa', name='cc')
    return {'value': get_cc_score(election, winners), 'dissat': get_cc_dissat(election, winners)}


def highest_hb_score(election, committee_size=1):
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None, 'dissat': None}
    winners, total_time = win.generate_winners(election=election,
                                             num_winners=committee_size,
                                             ballot="ordinal",
                                             type='borda_owa', name='hb')
    return {'value': get_hb_score(election, winners), 'dissat': get_hb_dissat(election, winners)}


def highest_pav_score(election, committee_size=1):
    if election.culture_id in LIST_OF_FAKE_MODELS:
        return {'value': None, 'dissat': None}
    winners, total_time = win.generate_winners(election=election,
                                             num_winners=committee_size,
                                             ballot="ordinal",
                                             type='bloc_owa', name='hb')
    return {'value': get_pav_score(election, winners), 'dissat': get_pav_dissat(election, winners)}


# HELPER FUNCTIONS
def _potes_to_unique_potes(potes):
    """ Remove repetitions from potes (positional votes) """
    unique_potes = []
    n = []
    for pote in potes:
        flag_new = True
        for i, p in enumerate(unique_potes):
            if list(pote) == list(p):
                n[i] += 1
                flag_new = False
        if flag_new:
            unique_potes.append(pote)
            n.append(1)
    return unique_potes, n


# GET SCORE
def get_score(election, winners, rule) -> float:
    if rule == 'cc':
        return get_cc_score(election, winners)
    elif rule == 'hb':
        return get_hb_score(election, winners)
    elif rule == 'pav':
        return get_pav_score(election, winners)


def get_cc_score(election, winners) -> float:
    num_voters = election.num_voters
    num_candidates = election.num_candidates
    votes = election.votes

    score = 0

    for i in range(num_voters):
        for j in range(num_candidates):
            if votes[i][j] in winners:
                score += num_candidates - j - 1
                break

    return score


def get_hb_score(election, winners) -> float:
    num_voters = election.num_voters
    num_candidates = election.num_candidates
    votes = election.votes

    score = 0

    for i in range(num_voters):
        ctr = 1.
        for j in range(num_candidates):
            if votes[i][j] in winners:
                score += (1. / ctr) * (num_candidates - j - 1)
                ctr += 1

    return score


def get_pav_score(election, winners) -> float:
    num_voters = election.num_voters
    num_candidates = election.num_candidates
    votes = election.votes

    score = 0

    vector = [0.] * num_candidates
    for i in range(len(winners)):
        vector[i] = 1.

    for i in range(num_voters):
        ctr = 1.
        for j in range(num_candidates):
            if votes[i][j] in winners:
                score += (1. / ctr) * vector[j]
                ctr += 1

    return score


# GET DISSAT
def get_dissat(election, winners, rule) -> float:
    if rule == 'cc':
        return get_cc_dissat(election, winners)
    elif rule == 'hb':
        return get_hb_dissat(election, winners)
    elif rule == 'pav':
        return get_pav_dissat(election, winners)


def get_cc_dissat(election, winners) -> float:

    num_voters = election.num_voters
    num_candidates = election.num_candidates

    dissat = 0

    for i in range(num_voters):
        for j in range(num_candidates):
            if election.votes[i][j] in winners:
                dissat += j
                break

    return dissat


def get_hb_dissat(election, winners) -> float:

    num_voters = election.num_voters
    num_candidates = election.num_candidates

    dissat = 0

    for i in range(num_voters):
        ctr = 1.
        for j in range(num_candidates):
            if election.votes[i][j] in winners:
                dissat += (1. / ctr) * (j)
                ctr += 1

    return dissat


def get_pav_dissat(election, winners) -> float:

    num_voters = election.num_voters
    num_candidates = election.num_candidates

    dissat = 0

    vector = [0. for _ in range(num_candidates)]
    for i in range(len(winners), num_candidates):
        vector[i] = 1.

    for i in range(num_voters):
        ctr = 1.
        for j in range(num_candidates):
            if election.votes[i][j] in winners:
                dissat += ((1. / ctr) * vector[j])
                ctr += 1

    return dissat


# OTHER
def borda_spread(election) -> int:
    """ Compute the difference between the highest and the lowest Borda score """
    c = election.num_candidates
    vectors = election.get_vectors()
    borda = [sum([vectors[i][pos] * (c - pos - 1) for pos in range(c)])
             for i in range(c)]
    return (max(borda)-min(borda)) * election.num_voters
