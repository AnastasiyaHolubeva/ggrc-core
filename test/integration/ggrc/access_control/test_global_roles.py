# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test Global roles permissions propagation"""

import ddt

from ggrc.models import all_models
from integration.ggrc.access_control import rbac_factories
from integration.ggrc.access_control.acl_propagation import base
from integration.ggrc.utils import helpers
from integration.ggrc.models import factories
from integration.ggrc_basic_permissions.models \
    import factories as permission_factories


@ddt.ddt
class TestWfAdminPropagation(base.TestACLPropagation):
  """Test Global roles permissions propagation"""
  PERMISSIONS = {
      "Creator": {
          "Workflow": {
              "create": True,
              "read": False,
              "update": False,
              "delete": False,
              "clone": False,
              "assign_wf_role": False,
          },
          "TaskGroup": {
              "create": False,
              "read": False,
              "update": False,
              "delete": False,
              "read_revisions": False,
              "map_control": False,
              "map_created_control": False,
              "read_mapped_control": False,
              "upmap_control": False,
              "clone": False,
              "assign": False,
          },
          "TaskGroupTask": {
              "create": False,
              "read": False,
              "update": False,
              "delete": False,
              "read_revisions": False,
              "assign": False,
          },
          "Cycle": {
              "create": False,
              "read": False,
              "update": False,
              "delete": False,
              "end": False,
          },
          "CycleTaskGroup": {
              "read": False,
              "update": False,
              "delete": False,
          },
          "CycleTask": {
              "create": False,
              "read": False,
              "update": False,
              "delete": False,
              "add_comment": False,
              "read_comment": (False, "unimplemented"),
              "map_control": False,
              "map_created_control": False,
              "read_mapped_control": False,
              "upmap_control": False,
              "start": False,
              "end": False,
              "verify": False,
              "deprecate": False,
              "decline": False,
              "restore": False,
              "assign": False,
              "delete_comment": False,
          },
      },
      "Reader": {
          "Workflow": {
              "create": (False, "unimplemented"),
              "read": True,
              "update": False,
              "delete": False,
              "clone": True,
              "activate": False,
              "assign_wf_role": False,
          },
          "TaskGroup": {
              "create": False,
              "read": True,
              "update": False,
              "delete": False,
              "map_control": False,
              "map_created_control": False,
              "upmap_control": False,
              "clone": False,
              "assign": False,
          },
          "TaskGroupTask": {
              "create": False,
              "read": True,
              "update": False,
              "delete": False,
              "assign": False,
          },
          "Cycle": {
              "read": True,
              "update": False,
              "delete": False,
              "end": False,
          },
          "CycleTaskGroup": {
              "read": True,
              "update": False,
              "delete": False,
          },
          "CycleTask": {
              "create": False,
              "read": True,
              "update": False,
              "delete": False,
              "add_comment": False,
              "read_comment": True,
              "map_control": False,
              "map_created_control": False,
              "upmap_control": False,
              "start": False,
              "end": False,
              "verify": False,
              "decline": False,
              "restore": False,
              "assign": False,
              "delete_comment": False,
              "deprecate": False,
          },
      },
      "Editor": {
          "Workflow": {
              "read": True,
              "update": True,
              "delete": True,
              "read_revisions": True,
              "clone": True,
              "activate": True,
              "assign_wf_role": True,
          },
          "TaskGroup": {
              "create": True,
              "read": True,
              "update": True,
              "read_revisions": True,
              "map_created_control": True,
              "read_mapped_control": True,
              "upmap_control": True,
              "clone": True,
              "delete": True,
              "assign": True,
          },
          "TaskGroupTask": {
              "create": True,
              "read": True,
              "update": True,
              "delete": True,
              "read_revisions": True,
              "assign": True,
          },
          "Cycle": {
              "read": True,
              "update": False,
              "delete": False,
              "end": False,
          },
          "CycleTaskGroup": {
              "read": True,
              "update": False,
              "delete": (False, "unimplemented"),
          },
          "CycleTask": {
              "create": True,
              "read": True,
              "update": True,
              "delete": False,
              "add_comment": True,
              "read_comment": True,
              "map_control": True,
              "map_created_control": True,
              "read_mapped_control": True,
              "upmap_control": True,
              "start": True,
              "end": True,
              "verify": True,
              "decline": True,
              "restore": True,
              "assign": True,
              "delete_comment": (True, "unimplemented"),
              "deprecate": True,
          },
      },
      "Administrator": {
          "Workflow": {
              "create": True,
              "read": True,
              "update": True,
              "delete": True,
              "clone": True,
              "activate": True,
              "assign_wf_role": True,
          },
          "TaskGroup": {
              "create": True,
              "read": True,
              "update": True,
              "delete": True,
              "map_control": True,
              "map_created_control": True,
              "upmap_control": True,
              "clone": True,
              "assign": True,
          },
          "TaskGroupTask": {
              "create": True,
              "read": True,
              "update": True,
              "delete": True,
              "assign": True,
          },
          "Cycle": {
              "read": True,
              "update": (False, "unimplemented"),
              "delete": False,
              "end": True,
          },
          "CycleTaskGroup": {
              "read": True,
              "update": False,
              "delete": (False, "unimplemented"),
          },
          "CycleTask": {
              "create": True,
              "read": True,
              "update": True,
              "delete": True,
              "add_comment": True,
              "read_comment": True,
              "map_control": True,
              "map_created_control": True,
              "upmap_control": True,
              "start": True,
              "end": True,
              "verify": True,
              "decline": True,
              "restore": True,
              "assign": True,
              "delete_comment": True,
              "deprecate": True,
          },
      },
  }

  def init_factory(self, role, model, parent):
    """Initialize RBAC factory with Global Admin role.

    Args:
        role: Global Custom authorization role (Creator/Reader/Editor).
        model: Model name for which factory should be got.
        parent: Model name in scope of which objects should be installed.

    Returns:
        Initialized RBACFactory object.
    """
    self.setup_people()
    admin_role = all_models.AccessControlRole.query.filter_by(
        name='Admin',
        object_type='Workflow',
    ).first()

    with factories.single_commit():
      user = factories.PersonFactory()
      permission_factories.UserRoleFactory(
          role=all_models.Role.query.filter_by(
              name="Administrator"
          ).first(),
          person=user
      )
    rbac_factory = rbac_factories.TEST_FACTORIES_MAPPING[model]
    return rbac_factory(
        user.id,
        admin_role,
        parent,
        authorization_user_id=self.people[role].id
    )

  @helpers.unwrap(PERMISSIONS)
  def test_access(self, role, model, action_name, expected_result):
    """Global {0:<7}: On {1:<20} test {2:<20} - Expected {3:<2} """
    self.runtest(role, model, action_name, expected_result)
