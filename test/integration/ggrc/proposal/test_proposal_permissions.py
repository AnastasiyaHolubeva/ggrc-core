# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test for proposal permissions."""

import json

import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc.api_helper import Api
from integration.ggrc.models import factories
from integration.ggrc.proposal import _get_query_proposal_request
from integration.ggrc_basic_permissions.models \
    import factories as rbac_factories


@ddt.ddt
class TestPermissions(TestCase):
  """Test checks permissions for proposals."""

  def setUp(self):
    super(TestPermissions, self).setUp()
    self.api = Api()
    roles = {r.name: r for r in all_models.Role.query.all()}
    factories.AccessControlRoleFactory(name="ACL_Reader", update=0,
                                       object_type="Program")
    factories.AccessControlRoleFactory(name="ACL_Editor",
                                       object_type="Program")
    factories.AccessControlRoleFactory(name="ACL_Nobody",
                                       object_type="Program",
                                       read=0,
                                       update=0,
                                       delete=0,)
    with factories.single_commit():
      self.program = factories.ProgramFactory()
      self.program.context.related_object = self.program
      self.people = {
          "Creator": factories.PersonFactory(),
          "Reader": factories.PersonFactory(),
          "Editor": factories.PersonFactory(),
          "Administrator": factories.PersonFactory(),
          "ACL_Reader": factories.PersonFactory(),
          "ACL_Editor": factories.PersonFactory(),
          "ACL_Nobody": factories.PersonFactory(),
          "Program Editors": factories.PersonFactory(),
          "Program Managers": factories.PersonFactory(),
          "Program Readers": factories.PersonFactory(),
      }
      for role_name in ["Creator", "Reader", "Editor", "Administrator"]:
        rbac_factories.UserRoleFactory(role=roles[role_name],
                                       person=self.people[role_name])
      for role_name in ["Program Editors",
                        "Program Managers",
                        "Program Readers"]:
        person = self.people[role_name]
        rbac_factories.UserRoleFactory(role=roles["Creator"], person=person)
        factories.AccessControlPersonFactory(
            ac_list=self.program.acr_name_acl_map[role_name],
            person=person,
        )
      self.proposal = factories.ProposalFactory(
          instance=self.program,
          content={
              "access_control_list": {},
              "custom_attribute_values": {},
              "fields": {},
              "mapping_fields": {},
              "mapping_list_fields": {},
          }
      )

      for role_name in ["ACL_Reader", "ACL_Editor", "ACL_Nobody"]:
        person = self.people[role_name]
        rbac_factories.UserRoleFactory(role=roles["Creator"], person=person)
        factories.AccessControlPersonFactory(
            ac_list=self.program.acr_name_acl_map[role_name],
            person=person,
        )

  @ddt.data(
      ("Creator", 403),
      ("Reader", 200),
      ("Editor", 200),
      ("ACL_Reader", 200),
      ("ACL_Editor", 200),
      ("ACL_Nobody", 403),
      ("Administrator", 200),
      ("Program Editors", 200),
      ("Program Managers", 200),
      ("Program Readers", 200),
  )
  @ddt.unpack
  def test_permissions_on_get(self, role_name, status):
    """Test get proposals for {0}."""
    proposal_id = self.proposal.id
    self.api.set_user(self.people[role_name])
    self.client.get("/login")
    resp = self.api.get(all_models.Proposal, proposal_id)
    self.assertEqual(status, resp.status_code)

  def api_proposal_status_change(self, proposal_id, status):
    return self.api.put(all_models.Proposal.query.get(proposal_id),
                        {"status": status})

  @ddt.data(
      ("Creator", 403),
      ("Reader", 403),
      ("Editor", 200),
      ("Administrator", 200),
      ("ACL_Reader", 403),
      ("ACL_Editor", 200),
      ("ACL_Nobody", 403),
      ("Program Editors", 200),
      ("Program Managers", 200),
      ("Program Readers", 403)
  )
  @ddt.unpack
  def test_permissions_on_apply(self, role_name, status):
    """Test apply proposals for {0}."""
    proposal_id = self.proposal.id
    self.api.set_user(self.people[role_name])
    self.client.get("/login")
    resp = self.api_proposal_status_change(proposal_id,
                                           all_models.Proposal.STATES.APPLIED)
    self.assertEqual(status, resp.status_code)

  @ddt.data(
      ("Creator", 403),
      ("Reader", 403),
      ("Editor", 200),
      ("ACL_Reader", 403),
      ("ACL_Editor", 200),
      ("ACL_Nobody", 403),
      ("Administrator", 200),
      ("Program Editors", 200),
      ("Program Managers", 200),
      ("Program Readers", 403),
  )
  @ddt.unpack
  def test_permissions_on_decline(self, role_name, status):
    """Test decline proposals for {0}."""
    proposal_id = self.proposal.id
    self.api.set_user(self.people[role_name])
    self.client.get("/login")
    resp = self.api_proposal_status_change(proposal_id,
                                           all_models.Proposal.STATES.DECLINED)
    self.assertEqual(status, resp.status_code)

  @ddt.data(
      ("Creator", 403),
      ("Reader", 201),
      ("Editor", 201),
      ("ACL_Reader", 201),
      ("ACL_Editor", 201),
      ("ACL_Nobody", 403),
      ("Administrator", 201),
      ("Program Editors", 201),
      ("Program Managers", 201),
      ("Program Readers", 201),
  )
  @ddt.unpack
  def test_permissions_on_create(self, role_name, status):
    """Test create proposal for {0}."""
    data = {
        "proposal": {
            "instance": {
                "id": self.program.id,
                "type": self.program.type,
            },
            "full_instance_content": {"title": "new_title"},
            "agenda": "update cav",
            "context": None,
        }
    }
    self.api.set_user(self.people[role_name])
    self.client.get("/login")
    resp = self.api.post(all_models.Proposal, data)
    self.assertEqual(status, resp.status_code)

  @ddt.data(
      ("Creator", 0),
      ("Reader", 1),
      ("Editor", 1),
      # Following two tests have been commented out as the functionality for
      # custom role propagation has been temporarily removed This test should
      # be enabled back in scope of ticket GGRC-4991
      # ("ACL_Reader", 1),
      # ("ACL_Editor", 1),
      ("ACL_Nobody", 0),
      ("Administrator", 1),
      ("Program Editors", 1),
      ("Program Managers", 1),
      ("Program Readers", 1),
  )
  @ddt.unpack
  def test_query_filter(self, role_name, expected_count):
    """Test query proposals for {0}.

    Args:
        role_name: string, unique key,
                   shows the position of user in generated infrustructure
        expected_count: int, number of proposals,
                        that should be filtered by query
    """
    program_id = self.program.id
    data = _get_query_proposal_request(program_id)
    self.api.set_user(self.people[role_name])
    self.client.get("/login")
    headers = {"Content-Type": "application/json", }
    resp = self.api.client.post("/query",
                                data=json.dumps(data),
                                headers=headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(expected_count, resp[0]["Proposal"]["count"])
