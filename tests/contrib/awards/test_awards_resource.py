# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 CERN.
#
# Invenio-Vocabularies is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test the award vocabulary resource."""

import json
from copy import deepcopy

import pytest
from invenio_db import db

from invenio_vocabularies.contrib.awards.api import Award


@pytest.fixture(scope="module")
def prefix():
    """API prefix."""
    return "awards"


def test_awards_invalid(client, h, prefix):
    """Test invalid type."""
    # invalid type
    res = client.get(f"{prefix}/invalid", headers=h)
    assert res.status_code == 404


def test_awards_forbidden(
    client, h, prefix, example_award, award_full_data
):
    """Test invalid type."""
    # invalid type
    award_full_data_too = deepcopy(award_full_data)
    award_full_data_too["pid"] = "other"
    res = client.post(
        f"{prefix}", headers=h, data=json.dumps(award_full_data_too))
    assert res.status_code == 403

    res = client.put(
        f"{prefix}/755021", headers=h, data=json.dumps(award_full_data))
    assert res.status_code == 403

    res = client.delete(f"{prefix}/755021")
    assert res.status_code == 403


def test_awards_get(client, example_award, h, prefix):
    """Test the endpoint to retrieve a single item."""
    id_ = example_award.id  # result_items wraps pid into id

    res = client.get(f"{prefix}/{id_}", headers=h)
    assert res.status_code == 200
    assert res.json["pid"] == id_
    # Test links
    assert res.json["links"] == {
        "self": "https://127.0.0.1:5000/api/awards/755021"
    }


def test_awards_search(client, example_award, h, prefix):
    """Test a successful search."""
    res = client.get(prefix, headers=h)

    assert res.status_code == 200
    assert res.json["hits"]["total"] == 1
    assert res.json["sortBy"] == "newest"

    res = client.get(f"{prefix}?q=755021", headers=h)

    assert res.status_code == 200
    assert res.json["hits"]["total"] == 1
    assert res.json["sortBy"] == "bestmatch"


@pytest.fixture(scope="function")
def example_awards(service, identity, indexer):
    """Create dummy awards with similar ids/numbers/titles."""
    awards_data = [
        {
            "title": {
                "en": "Host directed medicine in invasive fungal infection",
            },
            "pid": "847507",
            "number": "847507",
            "identifiers": [
                {
                    "identifier": "https://cordis.europa.eu/project/id/847507",
                    "scheme": "url"
                },
                {
                    "identifier": "10.3030/847507",
                    "scheme": "doi"
                }
            ]
        },
        {
            "title": {
                "en": "Palliative care in Parkinson disease",
            },
            "pid": "825785",
            "number": "825785",
            "identifiers": [
                {
                    "identifier": "https://cordis.europa.eu/project/id/825785",
                    "scheme": "url"
                },
                {
                    "identifier": "10.3030/825785",
                    "scheme": "doi"
                }
            ]

        }
    ]
    awards = []
    for data in awards_data:
        awards.append(service.create(identity, data))

    Award.index.refresh()  # Refresh the index

    yield

    for award in awards:
        award._record.delete(force=True)
        indexer.delete(award._record, refresh=True)
        db.session.commit()


def test_awards_suggest_sort(
    client, h, prefix, example_awards
):
    """Test a successful search."""

    # Should show 1 result
    res = client.get(f"{prefix}?suggest=847507", headers=h)
    assert res.status_code == 200
    assert res.json["hits"]["total"] == 1
    assert res.json["hits"]["hits"][0]["pid"] == "847507"

    # Should show 1 result
    res = client.get(f"{prefix}?suggest=Parkin", headers=h)
    assert res.status_code == 200
    assert res.json["hits"]["total"] == 1
    assert res.json["hits"]["hits"][0]["pid"] == "825785"

    # Should show 2 results, but pid=847507 as first due to created date
    res = client.get(f"{prefix}?suggest=8", headers=h)
    assert res.status_code == 200
    assert res.json["hits"]["total"] == 2
    assert res.json["hits"]["hits"][0]["pid"] == "847507"
    assert res.json["hits"]["hits"][1]["pid"] == "825785"


def test_awards_delete(
    client_with_credentials,
    h,
    prefix,
    identity,
    service,
    award_full_data,
    example_funder
):
    """Test a successful delete."""
    award = service.create(identity, award_full_data)
    id_ = award.id
    res = client_with_credentials.delete(f"{prefix}/{id_}", headers=h)
    assert res.status_code == 204

    # only the metadata is removed from the record, it is still resolvable
    res = client_with_credentials.get(f"{prefix}/{id_}", headers=h)
    assert res.status_code == 200
    base_keys = {"created", "updated", "id", "links", "revision_id", "pid"}
    assert set(res.json.keys()) == base_keys
    # not-ideal cleanup
    award._record.delete(force=True)


def test_awards_update(
    client_with_credentials, example_award, award_full_data, h, prefix
):
    """Test a successful update."""
    id_ = example_award.id
    new_title = "updated"
    award_full_data["title"]["en"] = new_title
    res = client_with_credentials.put(
        f"{prefix}/755021", headers=h, data=json.dumps(award_full_data))
    assert res.status_code == 200
    assert res.json["pid"] == id_  # result_items wraps pid into id
    assert res.json["title"]["en"] == new_title


def test_awards_create(
    client_with_credentials, award_full_data, h, prefix, example_funder
):
    """Tests a successful creation."""
    res = client_with_credentials.post(
        f"{prefix}", headers=h, data=json.dumps(award_full_data))
    assert res.status_code == 201
    assert res.json["pid"] == award_full_data["pid"]