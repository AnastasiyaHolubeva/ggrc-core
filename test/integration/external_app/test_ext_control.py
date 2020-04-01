# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for control model as external user."""

import datetime
import json
from email.utils import parseaddr

import ddt
import mock

from ggrc import db, settings
from ggrc.models import all_models
from ggrc.models.mixins import synchronizable
from integration.external_app.external_api_helper import ExternalApiClient
from integration.ggrc_workflows.models import factories as wf_factories
from integration.ggrc import TestCase
from integration.ggrc.models import factories
from integration.ggrc.utils.helpers import add_person_global_role


@ddt.ddt
class TestSyncServiceControl(TestCase):
  """Tests for control model using sync service as external user."""
  # pylint: disable=too-many-public-methods

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestSyncServiceControl, self).setUp()
    self.api = ExternalApiClient()

  @staticmethod
  def prepare_control_request_body():
    """Create payload for control creation."""
    test_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "id": 123,
        "title": "new_control",
        "context": None,
        "created_at": test_date,
        "updated_at": test_date,
        "slug": "CONTROL-01",
        "external_id": factories.SynchronizableExternalId.next(),
        "external_slug": factories.random_str(),
        "kind": "test kind",
        "means": "test means",
        "verify_frequency": "test frequency",
        "assertions": '["test assertion"]',
        "categories": '["test category"]',
        "review_status": all_models.Review.STATES.UNREVIEWED,
        "review_status_display_name": "some status",
        "due_date": test_date,
        "created_by": {
            "email": "creator@example.com",
            "name": "External Creator",
        },
        "last_submitted_at": test_date,
        "last_submitted_by": {
            "email": "owner@example.com",
            "name": "External Owner",
        },
        "last_verified_at": test_date,
        "last_verified_by": {
            "email": "compliance@example.com",
            "name": "External Compliance",
        },
    }

  @staticmethod
  def generate_minimal_control_body():
    """Generate minimal control body"""
    return {
        "id": 123,
        "title": factories.random_str(),
        "external_id": factories.SynchronizableExternalId.next(),
        "external_slug": factories.random_str(),
        "context": None,
        "review_status": all_models.Review.STATES.UNREVIEWED,
        "review_status_display_name": "some status",
    }

  @staticmethod
  def prepare_external_cad_body(definition_type, attribute_type):
    """Create payload for CAD.

    Args:
      definition_type: custom attribute definition type.
      attribute_type: object type.
    Returns:
      Dictionary with external cad payload.
    """
    return {
        "attribute_type": attribute_type,
        "context": None,
        "created_at": "2019-08-05T07:44:23",
        "definition_id": 444,
        "definition_type": definition_type,
        "helptext": "Help Text",
        "mandatory": False,
        "modified_by": None,
        "multi_choice_mandatory": None,
        "multi_choice_options": "",
        "placeholder": "Placeholder",
        "selfLink": "/api/custom_attribute_definitions/1",
        "title": "Attribute title",
        "type": "CustomAttributeDefinition",
        "updated_at": "2019-08-05T07:44:23",
    }

  @staticmethod
  def prepare_external_cav_body(obj_id, obj_type):
    """Create payload for CAV.

    Args:
      obj_id: Integer value of object id.
      obj_type: String representation of object type.
    Returns:
      Dictionary with external cav payload.
    """
    return {
        "attributable_id": obj_id,
        "attributable_type": obj_type,
        "attribute_object": None,
        "attribute_value": "Attribute value",
        "context": None,
        "created_at": "2019-08-05T07:45:19",
        "custom_attribute_id": 444,
        "modified_by": None,
        "preconditions_failed": None,
        "type": "CustomAttributeValue",
        "updated_at": "2019-08-05T07:45:19",
    }

  @staticmethod
  def setup_people(access_control_list):
    """Create Person objects specified in access_control_list."""
    all_users = set()
    for users in access_control_list.values():
      all_users.update({(user["email"], user["name"]) for user in users})

    with factories.single_commit():
      for email, name in all_users:
        factories.PersonFactory(email=email, name=name)

  def assert_obj_acl(self, obj, access_control_list):
    """Validate correctness of object access_control_list.

    Args:
        obj: Object for which acl should be checked.
        access_control_list: Dict of format
          {<role name>:[{"name": <user name>, "email": <user email>}.
    """
    actual_acl = {
        (user.acl_item.ac_role.name, user.person.email)
        for user in obj.access_control_list
    }
    expected_acl = {
        (role, person["email"])
        for role, people in access_control_list.items()
        for person in people
    }
    self.assertEqual(actual_acl, expected_acl)

  def assert_cav_fields(self, cav, expected_body):
    """Asserts that CAV fields are correct.

    Args:
      cav: CAV object.
      expected_body: Dictionary with expected CAV body.
    """
    self.assertEqual(
        cav.custom_attribute_id,
        expected_body["custom_attribute_id"]
    )
    self.assertEqual(
        cav.attributable_id,
        expected_body["attributable_id"]
    )
    self.assertEqual(
        cav.attributable_type,
        expected_body["attributable_type"]
    )
    self.assertEqual(
        cav.attribute_value,
        expected_body["attribute_value"]
    )

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  def test_control_create(self):
    """Test control creation using sync service."""
    control_body = self.prepare_control_request_body()
    app_user_email = "sync_service@example.com"
    ext_owner_email = "owner@example.com"
    ext_compliance_email = "compliance@example.com"

    response = self.api.post(all_models.Control, data={
        "control": control_body,
    })

    self.assertEqual(response.status_code, 201)
    id_ = response.json.get("control").get("id")
    self.assertEqual(control_body["id"], id_)
    control = db.session.query(all_models.Control).get(id_)
    app_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == app_user_email).one()
    ext_owner_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == ext_owner_email).one()
    ext_compliance_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == ext_compliance_email).one()
    self.assertEqual(control.modified_by_id, app_user.id)
    self.assertEqual(control.last_submitted_by_id, ext_owner_user.id)
    self.assertEqual(control.last_verified_by_id, ext_compliance_user.id)
    expected_assertions = control_body.pop("assertions")
    expected_categories = control_body.pop("categories")
    self.assertEqual(
        response.json["control"].get("assertions"),
        json.loads(expected_assertions)
    )
    self.assertEqual(
        response.json["control"].get("categories"),
        json.loads(expected_categories)
    )
    self.assert_response_fields(response.json.get("control"), control_body)
    self.assert_object_fields(control, control_body)
    self.assertEqual(control.assertions, expected_assertions)
    self.assertEqual(control.categories, expected_categories)
    revision = db.session.query(all_models.Revision).filter(
        all_models.Revision.resource_type == "Control",
        all_models.Revision.resource_id == control.id,
        all_models.Revision.action == "created",
        all_models.Revision.created_at == control.updated_at,
        all_models.Revision.updated_at == control.updated_at,
        all_models.Revision.modified_by_id == control.modified_by_id,
    ).one()
    self.assertIsNotNone(revision)

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  def test_create_control_with_cads(self):
    """Test create control with CADs/CAVs."""
    factories.CustomAttributeDefinitionFactory(
        id=444,
        attribute_type="Text",
        definition_type="control"
    )
    control_body = self.prepare_control_request_body()
    cad_body = self.prepare_external_cad_body("Text", "Control")
    cav_body = self.prepare_external_cav_body(123, "Control")
    control_body.update({
        "custom_attribute_definitions": [cad_body],
        "custom_attribute_values": [cav_body],
    })

    response = self.api.post(all_models.Control, data={
        "control": control_body,
    })

    self.assertEqual(response.status_code, 201)
    cav = all_models.CustomAttributeValue.query.one()
    self.assert_cav_fields(cav, cav_body)

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  def test_control_update(self):
    """Test control update using sync service."""
    test_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    _, email = parseaddr(settings.SYNC_SERVICE_USER)
    person = factories.PersonFactory(email=email)
    control = factories.ControlFactory(modified_by=person)
    response = self.api.get(control, control.id)
    response.json["control"].pop("selfLink")
    response.json["control"].pop("viewLink")
    control_body = response.json["control"]
    control_body.update({
        "title": "updated_title",
        "created_at": test_date,
        "updated_at": test_date,
        "kind": "test kind",
        "means": "test means",
        "verify_frequency": "test frequency",
        "assertions": '["test assertions"]',
        "categories": '["test categories"]',
    })

    response = self.api.put(
        control,
        control.id,
        data=response.json,
    )

    expected_assertions = control_body.pop("assertions")
    expected_categories = control_body.pop("categories")
    self.assertEqual(
        response.json["control"].get("assertions"),
        json.loads(expected_assertions),
    )
    self.assertEqual(
        response.json["control"].get("categories"),
        json.loads(expected_categories),
    )
    self.assert_response_fields(response.json["control"], control_body)
    control = all_models.Control.query.get(control.id)
    self.assert_object_fields(control, control_body)
    self.assertEqual(control.assertions, expected_assertions)
    self.assertEqual(control.categories, expected_categories)
    revision = db.session.query(all_models.Revision).filter(
        all_models.Revision.resource_type == "Control",
        all_models.Revision.resource_id == control.id,
        all_models.Revision.action == "modified",
        all_models.Revision.created_at == control.updated_at,
        all_models.Revision.updated_at == control.updated_at,
        all_models.Revision.modified_by_id == control.modified_by_id,
    ).one()
    self.assertIsNotNone(revision)

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  def test_update_control_with_cads(self):
    """Test update control with CADs/CAVs."""
    ext_user_email = "external@example.com"
    factories.CustomAttributeDefinitionFactory(
        id=444,
        attribute_type="Text",
        definition_type="control"
    )
    external_user = factories.PersonFactory(email=ext_user_email)
    control = factories.ControlFactory(id=123, modified_by=external_user)
    response = self.api.get(control, control.id)
    response_json = response.json
    cad_body = self.prepare_external_cad_body("Text", "Control")
    cav_body = self.prepare_external_cav_body(123, "Control")
    response_json["control"].update({
        "custom_attribute_definitions": [cad_body],
        "custom_attribute_values": [cav_body],
    })

    response = self.api.put(
        control,
        control.id,
        response_json
    )

    self.assertEqual(response.status_code, 200)
    cav = all_models.CustomAttributeValue.query.one()
    self.assert_cav_fields(cav, cav_body)

  def test_create_with_asserts(self):
    """Check control creation with assertions pass"""
    control_body = self.prepare_control_request_body()

    response = self.api.post(all_models.Control, data={
        "control": control_body,
    })

    self.assertEqual(response.status_code, 201)
    control = all_models.Control.query.first()
    self.assertIsNotNone(control)
    self.assertEqual('["test assertion"]', control.assertions)

  def test_set_control_end_date(self):
    """End_date can't to be updated."""
    control = factories.ControlFactory()

    self.api.put(control, control.id, {"end_date": "2015-10-10"})

    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNone(control.end_date)

  def test_set_deprecated_status(self):
    """Deprecated status setup end_date."""
    control = factories.ControlFactory()
    self.assertIsNone(control.end_date)

    self.api.put(control, control.id, {
        "status": all_models.Control.DEPRECATED,
    })

    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.end_date)

  def test_create_control_comments(self):
    """Test external comments creation for control."""
    control_body = self.prepare_control_request_body()
    response = self.api.post(all_models.Control, data={
        "control": control_body,
    })
    self.assertEqual(response.status_code, 201)

    response_ext_comment = self.api.post(all_models.ExternalComment, data={
        "external_comment": {
            "id": 1,
            "external_id": 1,
            "external_slug": factories.random_str(),
            "description": "test comment",
            "context": None,
        },
    })
    self.assertEqual(response_ext_comment.status_code, 201)
    response_relationship = self.api.post(all_models.Relationship, data={
        "relationship": {
            "source": {"id": 123, "type": "Control"},
            "destination": {"id": 1, "type": "ExternalComment"},
            "context": None,
            "is_external": True,
        },
    })
    self.assertEqual(response_relationship.status_code, 201)

    comments = db.session.query(all_models.ExternalComment.description).all()
    self.assertEqual(comments, [("test comment",)])
    rels = all_models.Relationship.query.filter_by(
        source_type="Control",
        source_id=123,
        destination_type="ExternalComment",
        destination_id=1
    )
    self.assertEqual(rels.count(), 1)

  def test_query_external_comment(self):
    """Test query endpoint for ExternalComments collection."""
    with factories.single_commit():
      control = factories.ControlFactory()
      comment = factories.ExternalCommentFactory(description="test comment")
      factories.RelationshipFactory(source=control, destination=comment)
    request_data = [{
        "filters": {
            "expression": {
                "object_name": "Control",
                "op": {
                    "name": "relevant"
                },
                "ids": [control.id]
            },
        },
        "object_name":"ExternalComment",
        "order_by": [{"name": "created_at", "desc": "true"}],
    }]

    response = self.api.post(
        comment,
        data=request_data,
        url="/query"
    )

    self.assert200(response)
    response_data = response.json[0]["ExternalComment"]
    self.assertEqual(response_data["count"], 1)
    self.assertEqual(response_data["values"][0]["description"], "test comment")

  @ddt.data("created_at", "description")
  def test_external_comments_order(self, order_by_attr):
    """Test order of ExternalComments returned by /query."""
    with factories.single_commit():
      control = factories.ControlFactory()
      for _ in range(5):
        comment = factories.ExternalCommentFactory(
            description=factories.random_str()
        )
        factories.RelationshipFactory(source=control, destination=comment)
    request_data = [{
        "filters": {
            "expression": {
                "object_name": "Control",
                "op": {
                    "name": "relevant"
                },
                "ids": [control.id]
            },
        },
        "object_name": "ExternalComment",
        "order_by": [{"name": order_by_attr, "desc": "true"}],
    }]

    response = self.api.post(
        comment,
        data=request_data,
        url="/query"
    )

    self.assert200(response)
    response_data = response.json[0]["ExternalComment"]
    comments = [val["description"] for val in response_data["values"]]
    expected_comments = db.session.query(
        all_models.ExternalComment.description
    ).order_by(
        getattr(all_models.ExternalComment, order_by_attr).desc(),
        all_models.ExternalComment.id.desc(),
    )
    self.assertEqual(comments, [i[0] for i in expected_comments])

  def test_create_unique_external_id(self):
    """Check control creation with non-unique external_id"""
    request1 = self.prepare_control_request_body()
    request2 = self.prepare_control_request_body()

    response1 = self.api.post(all_models.Control, data={'control': request1})
    prev_external_id = response1.json['control']['external_id']
    request2['external_id'] = prev_external_id
    response2 = self.api.post(all_models.Control, data={'control': request2})

    self.assert400(response2)

  @ddt.data("external_id",
            "review_status",
            "review_status_display_name",)
  def test_create_without_field(self, field):
    """Check control creation without 'field'"""
    request = self.prepare_control_request_body()
    del request[field]

    response = self.api.post(all_models.Control, data=request)

    self.assert400(response)

  @ddt.data("external_id",
            "review_status",
            "review_status_display_name",)
  # pylint: disable=invalid-name
  def test_control_create_with_empty_field(self, field):
    """Check control creation with empty 'field'"""
    request = self.prepare_control_request_body()
    request[field] = None

    response = self.api.post(all_models.Control, data=request)

    self.assert400(response)

  @ddt.data(
      ("external_id", factories.SynchronizableExternalId.next()),
      ("review_status", all_models.Review.STATES.REVIEWED),
      ("review_status_display_name", "value12345"))
  @ddt.unpack
  def test_control_update_field(self, field, new_value):
    """Test field is updated"""
    control = factories.ControlFactory()

    self.api.put(control, control.id, {field: new_value})

    control = db.session.query(all_models.Control).get(control.id)
    self.assertEquals(getattr(control, field), new_value)

  @ddt.data(
      ("external_id", "External ID"),
      ("review_status", "review_status"),
      ("review_status_display_name", "review_status_display_name"),
  )
  @ddt.unpack
  def test_update_field_to_null(self, field, field_name):
    """Test external_id is not set to None"""
    control = factories.ControlFactory()

    response = self.api.put(control, control.id, {field: None})

    self.assert400(response)
    self.assertEqual(response.json["message"],
                     field_name + " for the object is not specified")
    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.external_id)

  @ddt.data(
      ("kind", ["1", "2", "3"], "2"),
      ("means", ["1", "1", "1"], "1"),
      ("verify_frequency", ["3", "2", "3"], "3"),
  )
  @ddt.unpack
  def test_control_query_string(self, field, possible_values, search_value):
    """Test querying '{0}' field for control."""
    with factories.single_commit():
      for val in possible_values:
        factories.ControlFactory(**{field: val})
    request_data = [{
        'fields': [],
        'filters': {
            'expression': {
                'left': field,
                'op': {'name': '='},
                'right': search_value,
            },
        },
        'object_name': 'Control',
        'type': 'values',
    }]

    response = self.api.post(
        all_models.Control,
        data=request_data,
        url="/query"
    )

    self.assert200(response)
    response_data = response.json[0]["Control"]
    expected_controls = all_models.Control.query.filter_by(
        **{field: search_value}
    )
    self.assertEqual(expected_controls.count(), response_data.get("count"))
    expected_values = [getattr(i, field) for i in expected_controls]
    actual_values = [val.get(field) for val in response_data.get("values")]
    self.assertEqual(expected_values, actual_values)

  @ddt.data(
      ("assertions", ['["a", "b", "c"]', '["1", "2", "3"]'], "c"),
      ("categories", ['["a"]', '["1", "2", "3"]'], "1"),
      ("assertions", ['["a", "b"]', '["1", "2"]'], "3"),
  )
  @ddt.unpack
  def test_control_query_json(self, field, possible_values, search_value):
    """Test querying '{0}' field for control."""
    with factories.single_commit():
      for val in possible_values:
        factories.ControlFactory(**{field: val})
    request_data = [{
        "fields": [],
        "object_name": "Control",
        "type": "values",
        "filters": {
            "expression": {
                "left": field,
                "op": {"name": "="},
                "right": search_value,
            },
        },
    }]

    response = self.api.post(
        all_models.Control,
        data=request_data,
        url="/query"
    )

    self.assert200(response)
    response_data = response.json[0]["Control"]
    model_field = getattr(all_models.Control, field)
    expected_controls = all_models.Control.query.filter(
        model_field.like("%{}%".format(search_value))
    )
    self.assertEqual(expected_controls.count(), response_data.get("count"))
    expected_values = [
        json.loads(getattr(i, field)) for i in expected_controls
    ]
    actual_values = [val.get(field) for val in response_data.get("values")]
    self.assertEqual(expected_values, actual_values)

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  @ddt.data(
      {
          "Admin": {
              "email": "user1@example.com",
              "name": "user1",
          },
      },
      {
          "Admin": "user1@example.com",
      },
  )
  def test_control_invalid_acl_format(self, access_control_list):
    """Test creation of new object with acl in invalid format."""
    control_body = self.prepare_control_request_body()
    control_body.update({
        "access_control_list": access_control_list,
    })

    response = self.api.post(all_models.Control, data={
        "control": control_body
    })

    self.assert400(response)
    expected_err = synchronizable.RoleableSynchronizable.INVALID_ACL_ERROR
    self.assertEqual(response.json, expected_err)
    control = all_models.Control.query.filter_by(id=123)
    self.assertEqual(control.count(), 0)

  def test_control_with_tg_update(self):
    """Test updating of Control mapped to TaskGroup."""
    with factories.single_commit():
      control = factories.ControlFactory()
      task_group = wf_factories.TaskGroupFactory()
      factories.RelationshipFactory(
          source=task_group,
          destination=control
      )

    response = self.api.put(control, control.id, {
        "title": "new title",
        "task_groups": [],
    })

    self.assert200(response)
    control = all_models.Control.query.get(control.id)
    self.assertEqual(control.title, "new title")
    tg_ids = [id_[0] for id_ in db.session.query(all_models.TaskGroup.id)]
    self.assertEqual(len(tg_ids), 1)
    self.assertEqual([tg.source_id for tg in control.related_sources], tg_ids)
    tg_mapped_obj_ids = [
        id_[0] for id_ in db.session.query(
            all_models.Relationship.destination_id
        ).filter(
            all_models.Relationship.source_type == 'TaskGroup',
            all_models.Relationship.source_id.in_(tg_ids),
        )
    ]
    self.assertEqual(len(tg_mapped_obj_ids), 1)

  # pylint: disable=invalid-name
  def test_control_with_duplicated_title(self):
    """Test control with duplicated title."""
    control_1 = self.generate_minimal_control_body()
    control_2 = self.generate_minimal_control_body()
    control_2["title"] = control_1["title"]
    control_2["id"] = 1234

    response = self.api.post(all_models.Control, data={
        "control": control_1
    })
    self.assert201(response)
    response = self.api.post(all_models.Control, data={
        "control": control_2
    })
    self.assert201(response)

  def test_external_comment_acl(self):
    """Test automatic assigning current user to ExternalComment Admin."""
    response = self.api.post(all_models.ExternalComment, data={
        "external_comment": {
            "id": 1,
            "external_id": 1,
            "external_slug": factories.random_str(),
            "description": "test comment",
            "context": None,
            "access_control_list": {
                "Admin": [
                    {
                        "email": "user1@example.com",
                        "name": "user1",
                    },
                ],
            },
        }
    })

    self.assert201(response)
    comment = all_models.ExternalComment.query.get(1)
    comment_admin = comment.get_persons_for_rolename("Admin")
    self.assertEqual(
        [i.email for i in comment_admin],
        ["user1@example.com"]
    )

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  @ddt.data(
      {
          "Admin": [
              {
                  "email": "user1@example.com",
                  "name": "user1",
              },
          ],
      },
      {
          "Admin": [
              {
                  "email": "user1@example.com",
                  "name": "user1",
              },
              {
                  "email": "user2@example.com",
                  "name": "user2",
              },
          ],
          "Principal Assignees": [
              {
                  "email": "user2@example.com",
                  "name": "user2",
              },
              {
                  "email": "user3@example.com",
                  "name": "user3",
              },
          ]
      },
      {}
  )
  def test_control_acl_create(self, access_control_list):
    """Test creation of control with non empty acl."""
    control_body = self.prepare_control_request_body()
    control_body.update({
        "access_control_list": access_control_list,
    })
    self.setup_people(access_control_list)

    response = self.api.post(all_models.Control, data={
        "control": control_body
    })

    self.assert201(response)
    control = all_models.Control.query.get(123)
    self.assert_obj_acl(control, access_control_list)

  def test_control_acl_new_people_create(self):
    """Test creation of control with acl which contain new people."""
    control_body = self.prepare_control_request_body()
    access_control_list = {
        "Admin": [
            {
                "email": "user1@example.com",
                "name": "user1",
            },
            {
                "email": "user2@example.com",
                "name": "user2",
            },
        ]
    }
    control_body.update({
        "access_control_list": access_control_list,
    })

    response = self.api.post(all_models.Control, data={
        "control": control_body
    })

    self.assert201(response)
    for expected_person in access_control_list["Admin"]:
      user = all_models.Person.query.filter_by(
          email=expected_person["email"]
      ).one()
      self.assertEqual(user.name, expected_person["name"])
      self.assertEqual([ur.role.name for ur in user.user_roles], ["Creator"])
    control = all_models.Control.query.get(123)
    self.assert_obj_acl(control, access_control_list)

  def test_control_acl_update(self):
    """Test updating of control with non empty acl."""
    with factories.single_commit():
      control = factories.ControlFactory()
      person = factories.PersonFactory()
      control.add_person_with_role_name(person, "Admin")
    access_control_list = {
        "Admin": [
            {
                "email": "user1@example.com",
                "name": "user1",
            },
            {
                "email": "user2@example.com",
                "name": "user2",
            },
        ]
    }
    self.setup_people(access_control_list)

    response = self.api.put(control, control.id, {
        "access_control_list": access_control_list,
    })

    self.assert200(response)
    control = all_models.Control.query.get(control.id)
    self.assert_obj_acl(control, access_control_list)

  def test_control_acl_new_people_update(self):
    """Test updating of control with acl which contain new people."""
    person = factories.PersonFactory()
    add_person_global_role(person, 'Creator')
    with factories.single_commit():
      control = factories.ControlFactory()
      control.add_person_with_role_name(person, "Admin")
    access_control_list = {
        "Admin": [
            {
                "email": person.email,
                "name": person.name,
            }
        ],
        "Principal Assignees": [
            {
                "email": person.email,
                "name": person.name,
            },
            {
                "email": "user2@example.com",
                "name": "user2",
            },
            {
                "email": "user3@example.com",
                "name": "user3",
            },
        ]
    }

    response = self.api.put(control, control.id, {
        "access_control_list": access_control_list,
    })

    self.assert200(response)
    for expected_person in access_control_list["Admin"]:
      user = all_models.Person.query.filter_by(
          email=expected_person["email"]
      ).one()
      self.assertEqual(user.name, expected_person["name"])
      self.assertEqual([ur.role.name for ur in user.user_roles], ["Creator"])
    control = all_models.Control.query.get(control.id)
    self.assert_obj_acl(control, access_control_list)

  def test_wrong_role_controle_acl_update(self):
    """Test updating of control with non empty acl."""
    with factories.single_commit():
      control = factories.ControlFactory()
      person = factories.PersonFactory(name="user1", email="user1@example.com")
      control.add_person_with_role_name(person, "Admin")
    access_control_list = {
        "Non-existing role": [
            {
                "email": "user2@example.com",
                "name": "user2",
            },
        ]
    }

    response = self.api.put(control, control.id, {
        "access_control_list": access_control_list,
    })

    self.assert400(response)
    self.assertEqual(
        response.json["message"],
        "Role 'Non-existing role' does not exist"
    )
    control = all_models.Control.query.get(control.id)
    self.assert_obj_acl(
        control,
        {"Admin": [{"name": "user1", "email": "user1@example.com"}]}
    )
