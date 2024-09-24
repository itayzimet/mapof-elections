import copy
import logging
from time import time

import mapof.core.persistence.experiment_exports as exports
import numpy as np
from mapof.core.inner_distances import map_str_to_func
from mapof.core.objects.Experiment import Experiment
from tqdm import tqdm

from mapof.elections.objects.ApprovalElection import ApprovalElection
from mapof.elections.objects.OrdinalElection import OrdinalElection

from mapof.elections.distances import feature_distance
from mapof.elections.distances import main_approval_distances as mad
from mapof.elections.distances import main_ordinal_distances as mod
from mapof.elections.distances import positionwise_infty

registered_approval_distances = {
    'approvalwise': mad.compute_approvalwise_distance,

    'hamming': mad.compute_approvalwise_distance,  # unsupported distance
}

registered_ordinal_distances = {
    'positionwise_infty': positionwise_infty.positionwise_size_independent,
    'feature_l1': feature_distance.features_vector_l1,
    'feature_l2': feature_distance.features_vector_l2,
    'positionwise': mod.compute_positionwise_distance,
    'bordawise': mod.compute_bordawise_distance,
    'pairwise': mod.compute_pairwise_distance,
    'discrete': mod.compute_discrete_distance,

    'swap': mod.compute_swap_distance,
    'spearman': mod.compute_spearman_distance,
    'spearman_aa': mod.compute_spearman_distance_fastmap,

    'blank': mod.compute_blank_distance,

    'ilp_spearman': mod.compute_spearman_distance_ilp_py,  # unsupported distance
    'voterlikeness': mod.compute_voterlikeness_distance,  # unsupported distance
    'agg_voterlikeness': mod.compute_agg_voterlikeness_distance,  # unsupported distance
    'pos_swap': mod.compute_pos_swap_distance,  # unsupported distance
    'voter_subelection': mod.compute_voter_subelection,  # unsupported distance
    'candidate_subelection': mod.compute_candidate_subelection,  # unsupported distance
}


def add_approval_distance(name: str, function: callable) -> None:
    """
    Adds a new approval distance to the list of approval distances.

    Parameters
    ----------
        name
            Name of the distance.
        function
            function that computes the distance.

    Returns
    -------
        None.
    """
    registered_approval_distances[name] = function


def add_ordinal_distance(name: str, function: callable) -> None:
    """
    Adds a new ordinal distance to the list of ordinal distances.

    Parameters
    ----------
        name
            Name of the distance.
        function
            function that computes the distance.

    Returns
    -------
        None.
    """
    registered_ordinal_distances[name] = function


def get_distance(
        election_1,
        election_2,
        distance_id: str = None
) -> float or (float, list):
    """
    Computes distance between elections, (if applicable) optimal matching.

    Parameters
    ----------
        election_1
            First election.
        election_2
            Second election.
        distance_id
            Name of the distance.
    """

    if type(election_1) is ApprovalElection and type(election_2) is ApprovalElection:
        return get_approval_distance(election_1, election_2, distance_id=distance_id)
    elif type(election_1) is OrdinalElection and type(election_2) is OrdinalElection:
        return get_ordinal_distance(election_1, election_2, distance_id=distance_id)
    else:
        logging.warning('No such instance!')


def get_approval_distance(
        election_1: ApprovalElection,
        election_2: ApprovalElection,
        distance_id: str = None,
        **kwargs
) -> (float, list):
    """
    Computes distance between approval elections, (if applicable) optimal matching.

    Parameters
    ----------
        election_1
            First election.
        election_2
            Second election.
        distance_id
            Name of the distance.
    """

    inner_distance, main_distance = _extract_distance_id(distance_id)

    if main_distance in registered_approval_distances:

        if inner_distance is not None:
            return registered_approval_distances.get(main_distance)(election_1,
                                                                    election_2,
                                                                    inner_distance)
        else:
            return registered_approval_distances.get(main_distance)(election_1,
                                                                    election_2,
                                                                    **kwargs)

    else:
        logging.warning(f'No such distance as: {main_distance}!')


def get_ordinal_distance(
        election_1: OrdinalElection,
        election_2: OrdinalElection,
        distance_id: str = None, **kwargs
) -> float or (float, list):
    """
    Computes distance between ordinal elections, (if applicable) optimal matching.

    Parameters
    ----------
        election_1
            First election.
        election_2
            Second election.
        distance_id
            Name of the distance.
    """

    inner_distance, main_distance = _extract_distance_id(distance_id)

    if main_distance in registered_ordinal_distances:

        if inner_distance is not None:
            return registered_ordinal_distances.get(main_distance)(election_1,
                                                                   election_2,
                                                                   inner_distance)
        else:
            return registered_ordinal_distances.get(main_distance)(election_1,
                                                                   election_2,
                                                                   **kwargs)

    else:
        logging.warning(f'No such distance as: {main_distance}!')


def _extract_distance_id(distance_id: str) -> (callable, str):
    """ Return: inner distance (distance between votes) name and main distance name """
    if '-' in distance_id:
        inner_distance, main_distance = distance_id.split('-')
        inner_distance = map_str_to_func(inner_distance)
    else:
        main_distance = distance_id
        inner_distance = None
    return inner_distance, main_distance


def run_single_process(
        exp: Experiment,
        instances_ids: list,
        distances: dict,
        times: dict,
        matchings: dict,
        safe_mode: bool = False
) -> None:
    """ Single process for computing distances """

    for instance_id_1, instance_id_2 in tqdm(instances_ids, desc='Computing distances'):
        start_time = time()
        if safe_mode:
            distance = get_distance(copy.deepcopy(exp.instances[instance_id_1]),
                                    copy.deepcopy(exp.instances[instance_id_2]),
                                    distance_id=copy.deepcopy(exp.distance_id))
        else:
            distance = get_distance(exp.instances[instance_id_1],
                                    exp.instances[instance_id_2],
                                    distance_id=exp.distance_id)
        if type(distance) is tuple:
            distance, matching = distance
            matching = np.array(matching)
            matchings[instance_id_1][instance_id_2] = matching
            matchings[instance_id_2][instance_id_1] = np.argsort(matching)
        distances[instance_id_1][instance_id_2] = distance
        distances[instance_id_2][instance_id_1] = distances[instance_id_1][instance_id_2]
        times[instance_id_1][instance_id_2] = time() - start_time
        times[instance_id_2][instance_id_1] = times[instance_id_1][instance_id_2]


def run_multiple_processes(
        experiment: Experiment,
        instances_ids: list,
        distances: dict,
        times: dict,
        matchings: dict,
        process_id: int
) -> None:
    """ Single process for computing distances """

    for instance_id_1, instance_id_2 in tqdm(instances_ids,
                                             desc=f'Computing distances of thread {process_id}',
                                             position=process_id,
                                             leave=True):
        start_time = time()
        distance = get_distance(copy.deepcopy(experiment.instances[instance_id_1]),
                                copy.deepcopy(experiment.instances[instance_id_2]),
                                distance_id=copy.deepcopy(experiment.distance_id))
        if type(distance) is tuple:
            distance, matching = distance
            matching = np.array(matching)
            matchings[instance_id_1][instance_id_2] = matching
            matchings[instance_id_2][instance_id_1] = np.argsort(matching)
        distances[instance_id_1][instance_id_2] = distance
        distances[instance_id_2][instance_id_1] = distances[instance_id_1][instance_id_2]
        times[instance_id_1][instance_id_2] = time() - start_time
        times[instance_id_2][instance_id_1] = times[instance_id_1][instance_id_2]

    if experiment.is_exported:
        exports.export_distances_multiple_processes(experiment,
                                                    instances_ids,
                                                    distances,
                                                    times,
                                                    process_id)


__all__ = [
    'get_distance',
    'get_approval_distance',
    'get_ordinal_distance',
    'run_single_process',
    'run_multiple_processes'
]
