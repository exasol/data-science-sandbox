import contextlib
import docker
import json
import logging
import pytest
import re
import requests
import time

from exasol.ds.sandbox.lib.dss_docker import DssDockerImage
from test.ports import find_free_port
from dataclasses import dataclass

from test.integration.local_docker_registry import (
    LocalDockerRegistry,
)

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


def normalize_request_name(name: str):
    name = re.sub(r"[\[\]._]+", "_", name)
    return re.sub(r"^_+|_+$", "", name)


@dataclass
class DockerImageSpec:
    repository: str
    tag: str

    @property
    def name(self) -> str:
        return f"{self.repository}:{self.tag}"


@pytest.fixture(scope="session")
def registry_image():
    spec = DockerImageSpec("registry", "2")
    client = docker.from_env()
    if not client.images.list(spec.name):
        _logger.debug("Pulling Docker image with Docker registry")
        client.images.pull(spec.repository, spec.tag)
    return spec


@pytest.fixture(scope="session")
def sample_docker_image(registry_image):
    return registry_image


@contextlib.contextmanager
def tagged_image(old: DockerImageSpec, new: DockerImageSpec):
    """
    Prepend host and port of LocalDockerRegistry to the repository name of the
    DssDockerImage to enable pushing the image to the local registry.
    """
    client = docker.from_env()
    _logger.debug(f'tagging image from {old.name} to {new.name}')
    image = client.images.get(old.name)
    image.tag(new.repository, new.tag)
    tagged = DssDockerImage(new.repository, new.tag)
    try:
        yield tagged
    finally:
        docker.from_env().images.remove(new.name)


@pytest.fixture(scope="session")
def docker_registry(request, registry_image):
    """
    Provide a context for creating a LocalDockerRegistry accepting
    parameter ``repository``.

    You can provide cli option ``--docker-registry HOST:PORT`` to pytest in
    order reuse an already running Docker container as registry.
    """
    existing = request.config.getoption("--docker-registry")
    if existing is not None:
        yield LocalDockerRegistry(existing)
        return

    test_name = normalize_request_name(request.node.name)
    container_name = f"{test_name}_registry"

    port = find_free_port()
    client = docker.from_env()
    _logger.debug(f"Starting container {container_name}")
    try:
        client.containers.get(container_name).remove(force=True)
    except:
        pass
    container = client.containers.run(
        image="registry:2",
        name=container_name,
        ports={5000: port},
        detach=True,
    )
    time.sleep(10)
    _logger.debug(f"Finished starting container {container_name}")
    try:
        yield LocalDockerRegistry(f"localhost:{port}")
    finally:
        _logger.debug("Stopping container")
        container.stop()
        _logger.debug("Removing container")
        container.remove()


def test_push_tag(sample_docker_image, docker_registry):
    old = DockerImageSpec("registry", "2")
    repo = "org/sample_repo"
    new = DockerImageSpec(
        docker_registry.host_and_port + "/" + repo,
        "999.9.9",
    )
    with tagged_image(old, new) as tagged:
        docker_registry.push(tagged.repository, new.tag)
    assert repo in docker_registry.repositories
    assert new.tag in docker_registry.images(repo)["tags"]
