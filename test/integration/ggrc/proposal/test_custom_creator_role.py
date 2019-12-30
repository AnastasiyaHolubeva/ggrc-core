# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test for proposal in case of usage of custom creator role"""

import json
import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc.access_control import acl_helper
from integration.ggrc.api_helper import Api
from integration.ggrc.models import factories
from integration.ggrc.proposal import _get_query_proposal_request
from integration.ggrc_basic_permissions.models \
    import factories as rbac_factories
from integration.ggrc.query_helper import WithQueryApi


@ddt.ddt
class TestOwnerAccess(TestCase, WithQueryApi):
  """Ensure that global creator has access to created proposal by him"""

  def setUp(self):
    super(TestOwnerAccess, self).setUp()
    self.client.get("/login")
    self.api = Api()

  @staticmethod
  def _get_create_proposal_request(program_id, acr_id, person_id):
    """Prepare dict with proposal creation request"""

    return {
        "proposal": {
            "instance": {
                "id": program_id,
                "type": all_models.Program.__name__,
            },
            "full_instance_content": {"title": "new_title"},
            "agenda": "update cav",
            "context": None,
            "access_control_list": [acl_helper.get_acl_json(acr_id, person_id)]
        }
    }

  def test_admin_has_access(self):
    """Ensure that global creator has access to created proposal by him"""
    role_creator = all_models.Role.query.filter(
        all_models.Role.name == "Creator").one()

    # prepare - create program, assign roles
    factories.AccessControlRoleFactory(name="ACL_Reader", update=0,
                                       object_type="Program")
    with factories.single_commit():
      program = factories.ProgramFactory()
      person = factories.PersonFactory()
      rbac_factories.UserRoleFactory(role=role_creator, person=person)
      factories.AccessControlPersonFactory(
          ac_list=program.acr_name_acl_map["ACL_Reader"],
          person=person,
      )
      program_id = program.id

    # make query to create proposal
    self.api.set_user(person)
    self.client.get("/login")

    acr_class = all_models.AccessControlRole
    acr = acr_class.query.filter(acr_class.name == 'ProposalEditor',
                                 acr_class.object_type == 'Proposal').one()

    create_data = self._get_create_proposal_request(
        program_id, acr.id, person.id)
    self.api.post(all_models.Proposal, create_data)

    query_data = _get_query_proposal_request(program_id)
    headers = {"Content-Type": "application/json", }
    resp = self.api.client.post("/query",
                                data=json.dumps(query_data),
                                headers=headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(resp[0]["Proposal"]["count"], 1)

  def test_nonadmin_has_access(self):
    """Test access to proposal for non creator of proposal"""
    role_creator = all_models.Role.query.filter(
        all_models.Role.name == "Creator").one()

    # prepare - create program, assign roles
    factories.AccessControlRoleFactory(name="ACL_Reader", update=0,
                                       object_type="Program")
    with factories.single_commit():
      program = factories.ProgramFactory()
      person1 = factories.PersonFactory()
      person2 = factories.PersonFactory()
      for person in (person1, person2):
        rbac_factories.UserRoleFactory(role=role_creator, person=person)
        factories.AccessControlPersonFactory(
            ac_list=program.acr_name_acl_map["ACL_Reader"],
            person=person,
        )
      program_id = program.id
      person2_id = person2.id

    # make query to create proposal by person1
    self.api.set_user(person1)
    self.client.get("/login")

    acr_class = all_models.AccessControlRole
    acr = acr_class.query.filter(acr_class.name == 'ProposalEditor',
                                 acr_class.object_type == 'Proposal').one()

    create_data = self._get_create_proposal_request(
        program_id, acr.id, person1.id)
    self.api.post(all_models.Proposal, create_data)

    # login as person2 and make request
    self.api.set_user(all_models.Person.query.get(person2_id))
    self.client.get("/login")

    query_data = _get_query_proposal_request(program_id)
    headers = {"Content-Type": "application/json", }
    resp = self.api.client.post("/query",
                                data=json.dumps(query_data),
                                headers=headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(resp[0]["Proposal"]["count"], 1)

  @ddt.data("Program Readers",
            "Program Editors",
            "Program Managers",
            "Primary Contacts",
            "Secondary Contacts")
  def test_program_read_as_creator(self, program_role):
    """Test access to proposal for {0}"""
    with factories.single_commit():
      program = factories.ProgramFactory()
      program_manager = factories.PersonFactory()
      factories.AccessControlPersonFactory(
          ac_list=program.acr_name_acl_map["Program Managers"],
          person=program_manager,
      )
      program_id = program.id

    # make query to create proposal by program_manager
    self.api.set_user(program_manager)
    self.client.get("/login")

    acr_class = all_models.AccessControlRole
    acr = acr_class.query.filter(acr_class.name == 'ProposalEditor',
                                 acr_class.object_type == 'Proposal').one()

    create_data = self._get_create_proposal_request(
        program_id, acr.id, program_manager.id)
    self.api.post(all_models.Proposal, create_data)

    query_data = _get_query_proposal_request(program_id)
    headers = {"Content-Type": "application/json", }
    resp = self.api.client.post("/query",
                                data=json.dumps(query_data),
                                headers=headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(resp[0]["Proposal"]["count"], 1)

    role_creator = all_models.Role.query.filter(
        all_models.Role.name == "Creator").one()

    # make query to check proposals by Creator role person
    with factories.single_commit():
      person = factories.PersonFactory()
      rbac_factories.UserRoleFactory(role=role_creator, person=person)
      factories.AccessControlPersonFactory(
          ac_list=program.acr_name_acl_map[program_role],
          person=person,
      )

    self.api.set_user(person)
    self.client.get("/login")

    query_data = _get_query_proposal_request(program_id)
    headers = {"Content-Type": "application/json", }
    resp = self.api.client.post("/query",
                                data=json.dumps(query_data),
                                headers=headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(resp[0]["Proposal"]["count"], 1)

  def test_program_new_role_read(self):
    """Test access to proposal for program newly reader role"""
    # prepare - create program, assign roles
    role_name = "Test Read only ACL"
    with factories.single_commit():
      factories.AccessControlRoleFactory(
          name=role_name, update=0, delete=0, object_type="Program")
      program = factories.ProgramFactory()
      program_manager = factories.PersonFactory()
      factories.AccessControlPersonFactory(
          ac_list=program.acr_name_acl_map["Program Managers"],
          person=program_manager,
      )
      program_id = program.id

    # make query to create proposal by program_manager
    self.api.set_user(program_manager)
    self.client.get("/login")

    acr_class = all_models.AccessControlRole
    acr = acr_class.query.filter(
        acr_class.name == 'ProposalEditor',
        acr_class.object_type == 'Proposal'
    ).one()

    create_data = self._get_create_proposal_request(
        program_id, acr.id, program_manager.id)
    self.api.post(all_models.Proposal, create_data)

    query_data = _get_query_proposal_request(program_id)
    resp = self.api.client.post("/query",
                                data=json.dumps(query_data),
                                headers=self.headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(resp[0]["Proposal"]["count"], 1)

    role_creator = all_models.Role.query.filter(
        all_models.Role.name == "Creator").one()

    # make query to check proposals by Creator role person
    with factories.single_commit():
      person = factories.PersonFactory()
      rbac_factories.UserRoleFactory(role=role_creator, person=person)
      factories.AccessControlPersonFactory(
          ac_list=program.acr_name_acl_map[role_name],
          person=person,
      )

    self.api.set_user(person)
    self.client.get("/login")

    query_data = _get_query_proposal_request(program_id)
    resp = self.api.client.post("/query",
                                data=json.dumps(query_data),
                                headers=self.headers).json
    self.assertEqual(1, len(resp))
    self.assertEqual(resp[0]["Proposal"]["count"], 1)
