# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for Risk model as external user."""

import datetime

import ddt

from ggrc import db
from ggrc.models import all_models
from integration.external_app.external_api_helper import ExternalApiClient
from integration.ggrc import TestCase
from integration.ggrc.generator import ObjectGenerator
from integration.ggrc.models import factories


@ddt.ddt
class TestSyncServiceRisk(TestCase):
  """Tests for risk model for GGRCQ users."""

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestSyncServiceRisk, self).setUp()
    self.api = ExternalApiClient()

  @staticmethod
  def generate_risk_body():
    """Generate JSON body for Risk."""
    test_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    body = {
        "id": 10,
        "title": "External risk",
        "risk_type": "External risk",
        "created_at": test_date,
        "updated_at": test_date,
        "external_id": 10,
        "external_slug": "external_slug",
        "review_status": all_models.Review.STATES.UNREVIEWED,
        "review_status_display_name": "some status",
    }

    return body

  @staticmethod
  def generate_comment_body():
    """Generate JSON body for Risk comment."""
    body = {
        "id": 1,
        "external_id": 1,
        "external_slug": factories.random_str(),
        "description": "External comment",
        "context": None,
    }

    return body

  def assert_instance(self, expected, risk):
    """Compare expected response body with actual."""
    risk_values = {}
    expected_values = {}

    for field, value in expected.items():
      expected_values[field] = value
      attr = getattr(risk, field, None)
      if isinstance(attr, datetime.datetime):
        # this is datetime object
        attr = attr.strftime("%Y-%m-%d")
      risk_values[field] = attr

    self.assertEqual(expected_values, risk_values)

  def test_create_risk(self):
    """Test risk create with external user."""
    risk_body = self.generate_risk_body()

    response = self.api.post(
        all_models.Risk,
        data={"risk": risk_body},
    )

    self.assert201(response)
    risk = all_models.Risk.query.get(risk_body["id"])
    self.assert_instance(risk_body, risk)

  @ddt.data('review_status',
            'review_status_display_name',
            'id')
  # pylint: disable=invalid-name
  def test_create_risk_without_field(self, field):
    """Check risk creation without review_status"""
    risk_body = self.generate_risk_body()
    del risk_body[field]

    response = self.api.post(all_models.Risk, data=risk_body)

    self.assert400(response)

  @ddt.data('review_status',
            'review_status_display_name',
            'id')
  # pylint: disable=invalid-name
  def test_create_risk_with_empty_field(self, field):
    """Check risk creation with empty review_status"""
    risk_body = self.generate_risk_body()
    risk_body[field] = None

    response = self.api.post(all_models.Risk, data=risk_body)

    self.assert400(response)

  def test_update_risk(self):
    """Test risk update with external user."""
    test_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    with factories.single_commit():
      risk_id = factories.RiskFactory().id
    created_at = test_date
    updated_at = test_date
    new_values = {
        "title": "New risk",
        "created_at": created_at,
        "updated_at": updated_at,
        "review_status": all_models.Review.STATES.UNREVIEWED,
        "review_status_display_name": "some status",
    }
    risk = all_models.Risk.query.get(risk_id)

    response = self.api.put(risk, risk.id, new_values)

    self.assert200(response)
    risk = all_models.Risk.query.get(risk_id)
    self.assert_instance(new_values, risk)

  @ddt.data(
      ("review_status", "Review status"),
      ("review_status_display_name", "Review status display")
  )
  @ddt.unpack
  # pylint: disable=invalid-name
  def test_update_risk_field_to_null(self, field, field_name):
    """Test review_status is not set to None"""
    risk = factories.RiskFactory()

    response = self.api.put(risk, risk.id, {
        field: None,
    })

    self.assert400(response)
    self.assertEqual(response.json["message"],
                     field_name + " for the object is not specified")
    risk = db.session.query(all_models.Risk).get(risk.id)
    self.assertIsNotNone(risk.external_id)

  # pylint: disable=invalid-name
  def test_update_review_status(self):
    """Test review_status is updated"""
    risk = factories.RiskFactory()
    new_value = all_models.Review.STATES.REVIEWED

    self.api.put(risk, risk.id, {
        "review_status": new_value,
        "review_status_display_name": "some status"
    })

    risk = db.session.query(all_models.Risk).get(risk.id)
    self.assertEquals(risk.review_status, new_value)

  # pylint: disable=invalid-name
  def test_update_review_status_display_name(self):
    """Test review_status_display_name is updated"""
    risk = factories.RiskFactory()
    new_value = "test123"

    self.api.put(risk, risk.id, {
        "review_status_display_name": new_value,
        "review_status": all_models.Review.STATES.UNREVIEWED
    })

    risk = db.session.query(all_models.Risk).get(risk.id)
    self.assertEquals(risk.review_status_display_name, new_value)

  def test_create_risk_comments(self):
    """Test external comments creation for risk."""
    risk_body = self.generate_risk_body()
    response = self.api.post(all_models.Risk, data={
        "risk": risk_body,
    })
    self.assert201(response)
    comment_body = self.generate_comment_body()

    response_ext_comment = self.api.post(all_models.ExternalComment, data={
        "external_comment": comment_body,
    })

    self.assert201(response_ext_comment)
    comment = db.session.query(all_models.ExternalComment.description).one()
    self.assertEqual(comment, (comment_body["description"],))
    risk_id = db.session.query(all_models.Risk.id).one()[0]
    comment_id = db.session.query(all_models.ExternalComment.id).one()[0]

    response_relationship = self.api.post(all_models.Relationship, data={
        "relationship": {
            "source": {"id": risk_id, "type": "Risk"},
            "destination": {"id": comment_id, "type": "ExternalComment"},
            "context": None,
            "is_external": True
        },
    })

    self.assert201(response_relationship)
    rels = all_models.Relationship.query.filter_by(
        source_type="Risk",
        source_id=risk_id,
        destination_type="ExternalComment",
        destination_id=comment_id
    )
    self.assertEqual(rels.count(), 1)

  def test_get_risk_external_comment(self):
    """Test query endpoint for risk ExternalComments."""
    with factories.single_commit():
      risk = factories.RiskFactory()
      comment = factories.ExternalCommentFactory(description="comment")
      factories.RelationshipFactory(source=risk, destination=comment)
    request_data = [{
        "filters": {
            "expression": {
                "object_name": "Risk",
                "op": {
                    "name": "relevant"
                },
                "ids": [risk.id]
            },
        },
        "object_name":"ExternalComment",
        "order_by": [{"name": "created_at", "desc": "true"}],
    }]

    response = self.api.post(
        all_models.Risk,
        data=request_data,
        url="/query",
    )

    self.assert200(response)
    response_data = response.json[0]["ExternalComment"]
    self.assertEqual(response_data["count"], 1)
    self.assertEqual(response_data["values"][0]["description"], "comment")

  @ddt.data(
      ("Due Date", "due_date"),
      ("Last Owner Reviewed Date", "last_submitted_at"),
      ("Last Compliance Reviewed Date", "last_verified_at"),
  )
  @ddt.unpack
  def test_search_risk_by_dates(self, field, attr):
    """Test query endpoint for risk by dates."""
    current_date = datetime.date.today()
    with factories.single_commit():
      factories.RiskFactory(**{attr: current_date})
    request_data = [{
        "filters": {
            "expression": {
                "left": {"left": field,
                         "op": {"name": "~"},
                         "right": current_date.strftime("%Y-%m-%d")},
                "op": {"name": "AND"},
                "right": {"left": "Status",
                          "op": {"name": "IN"},
                          "right": ["Active", "Draft", "Deprecated"]}
            }
        },
        "object_name": "Risk",
        "order_by": [{"name": "updated_at", "desc": "true"}],
    }]

    response = self.api.post(
        all_models.Risk,
        data=request_data,
        url="/query",
    )

    self.assert200(response)
    response_data = response.json[0]["Risk"]
    self.assertEqual(response_data["count"], 1)
    self.assertEqual(response_data["values"][0][attr],
                     current_date.strftime("%Y-%m-%d"))

  @ddt.data(
      ("Created By", "created_by"),
      ("Last Owner Reviewed By", "last_submitted_by"),
      ("Last Compliance Reviewed By", "last_verified_by"),
  )
  @ddt.unpack
  def test_search_risk_by_users(self, field, attr):
    """Test query endpoint for risk by users."""
    with factories.single_commit():
      person = factories.PersonFactory()
      factories.RiskFactory(**{attr: person})
    request_data = [{
        "filters": {
            "expression": {
                "left": {"left": field,
                         "op": {"name": "~"},
                         "right": person.email},
                "op": {"name": "AND"},
                "right": {"left": "Status",
                          "op": {"name": "IN"},
                          "right": ["Active", "Draft", "Deprecated"]}
            }
        },
        "object_name": "Risk",
        "order_by": [{"name": "updated_at", "desc": "true"}],
    }]

    response = self.api.post(
        all_models.Risk,
        data=request_data,
        url="/query",
    )

    self.assert200(response)
    response_data = response.json[0]["Risk"]
    self.assertEqual(response_data["count"], 1)
    self.assertEqual(response_data["values"][0][attr]['email'],
                     person.email)


class TestRiskSnapshotting(TestCase):
  """Risk snapshot tests"""
  def setUp(self):
    """setUp, nothing else to add."""
    super(TestRiskSnapshotting, self).setUp()
    self.api = ExternalApiClient(use_ggrcq_service_account=True)
    self.objgen = ObjectGenerator()

  def test_update_risk_snapshot(self):
    """Update risk snapshot to the latest version"""
    with factories.single_commit():
      program = factories.ProgramFactory(title="P1")
      risk = factories.RiskFactory(title="R1")
      risk_id = risk.id
      factories.RelationshipFactory(source=program, destination=risk)
    # Risk snapshot created for audit during mapping audit to program
    self.objgen.generate_object(all_models.Audit, {
        "title": "A1",
        "program": {"id": program.id},
        "status": "Planned",
        "snapshots": {
            "operation": "create",
        },
    })
    # Update risk to get outdated snapshot (new risk revision)
    risk = all_models.Risk.query.get(risk_id)
    self.api.put(risk, risk.id, {
        "title": "New risk title",
    })
    audit = all_models.Audit.query.filter_by(title="A1").one()
    snapshot = all_models.Snapshot.query.first()
    self.assertEquals(audit, snapshot.parent)

    # Update snapshot to the latest revision
    response = self.api.put(snapshot, snapshot.id, {
        "update_revision": "latest",
    })

    self.assert200(response)
    self.assertTrue(response.json["snapshot"]["is_latest_revision"])
