from typing import Optional, Dict

import gym

from regym.environments.gym_parser import parse_gym_environment
from regym.environments.unity_parser import parse_unity_environment
from regym.environments.task import Task, EnvType


def generate_task(env_name: str, env_type: EnvType = EnvType.SINGLE_AGENT, **kwargs: Optional[Dict]) -> Task:
    '''
    Returns a regym.environments.Task by creating an environment derived from :param: env_name
    optionally parameterized by :param: kwargs. The resulting Task extracts relevant information
    used for build regym.rl_algorithms.agents able to act in said Task.
    If :param: env_name matches a registered OpenAI Gym environment it will create it from there
    If :param: env_name points to a (platform specific) UnityEnvironment executable, it will generate a Unity environment
    In the case of :param: env_name being detected as both an OpenAI Gym and Unity environmet, an error will be raised

    :param env_name: String identifier for the environment to be created
    :param env_type: Determines whether the parameter is (single/multi)-agent
                     and how are the environment processes these actions
                     (i.e all actions simultaneously, or sequentially)
    :param kwargs: Keyword arguments to be passed as parameters to the underlying environment
    :returns: Task created from :param: env_name
    '''
    if env_name is None: raise ValueError('Parameter \'env_name\' was None')
    is_gym_environment = any([env_name == spec.id for spec in gym.envs.registry.all()]) # Checks if :param: env_name was registered
    is_unity_environment = check_for_unity_executable(env_name)
    if is_gym_environment and is_unity_environment: raise ValueError(f'{env_name} exists as both a Gym and an Unity environment. Rename Unity environment to remove duplicate problem.')
    if is_gym_environment: return parse_gym_environment(gym.make(env_name, **kwargs), env_type)
    if is_unity_environment: return parse_unity_environment(env_name, env_type, kwargs)
    else: raise ValueError(f'Environment \'{env_name}\' was not recognized as either a Gym nor a Unity environment')


def check_for_unity_executable(env_name):
    '''
    Checks if :param: env_name points to a Unity Executable
    :param env_name: String identifier for the environment to be created
    :returns: Boolean whether :param: env_name is a Unity executable
    '''
    import os, platform
    valid_extensions = {'Linux': '.x86_64', 'Darwin': '.app', 'Windows': '.exe'}
    return os.path.isfile(env_name + valid_extensions[platform.system()])
