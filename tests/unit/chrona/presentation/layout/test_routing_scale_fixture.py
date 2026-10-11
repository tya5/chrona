"""The performance record must use the issue's actual published inputs."""
import random

import pytest

from tests.support.routing_scale import routing_scale_project


@pytest.mark.parametrize(("size", "relation_count"), ((200, 46), (1000, 228)))
def test_published_scale_counts_and_repeated_identity(size, relation_count):
    state = random.getstate()
    project = routing_scale_project(size)
    assert len(project["objects"]) == size
    assert len(project["relations"]) == relation_count
    assert project == routing_scale_project(size)
    assert random.getstate() == state
    for relation in project["relations"]:
        source = project["objects"][relation["from"]["object"]]
        target = project["objects"][relation["to"]["object"]]
        assert source["parent"] == target["parent"]
        assert source["schedule"]["start"] <= target["schedule"]["start"]


@pytest.mark.parametrize("size", (200, 1000))
def test_published_no_relation_controls(size):
    project = routing_scale_project(size, dependencies=False)
    assert len(project["objects"]) == size
    assert project["relations"] == []
