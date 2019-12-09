# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Cycle Task RBAC Factory."""
from datetime import datetime

from ggrc import access_control
from ggrc.models import all_models
from integration.ggrc import Api, generator
from integration.ggrc.access_control.rbac_factories import base
from integration.ggrc.models import factories
from integration.ggrc_basic_permissions.models \
    import factories as permission_factories


class CycleTaskRBACFactory(base.BaseRBACFactory):
  """Cycle Task RBAC factory class."""

  def __init__(self, user_id, acr, parent=None, authorization_user_id=None):
    """Set up objects for Cycle Task permission tests.

    Args:
        user_id: Id of user under which scope objects will be created.
        acr: Instance of ACR that should be assigned for tested user.
        parent: Model name in scope of which objects should be set up.
        authorization_user_id: Id of user to authorization.

    """
    # pylint: disable=unused-argument
    self.setup_workflow_scope(user_id, acr)

    self.admin_control_id = {
        name: id for id, name
        in access_control.role.get_custom_roles_for("Control").items()
    }["Admin"]

    self.api = Api()
    self.objgen = generator.ObjectGenerator()
    self.objgen.api = self.api
    _, self.comment = self.objgen.generate_object(
        all_models.Comment,
        {
            "description": factories.random_str(),
            "context": None,
        }
    )
    self.setup_user(user_id, authorization_user_id)

  def create(self):
    """Create new Cycle Task object."""
    cycle_tg = all_models.CycleTaskGroup.query.first()
    return self.api.post(all_models.CycleTaskGroupObjectTask, {
        "cycle_task_group_object_task": {
            "title": "New Cycle Task",
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "context": None,
            "task_type": "text",
            "cycle_task_group": {
                "id": cycle_tg.id,
                "type": "Task Group",
            },
            "cycle": {
                "id": cycle_tg.cycle.id,
                "type": "Cycle",
            },
        }
    })

  def read(self):
    """Read existing Cycle Task object."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.get(cycle_task, cycle_task.id)

  def update(self):
    """Update title of existing Cycle Task object."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"title": factories.random_str()})

  def delete(self):
    """Delete Cycle Task object."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.delete(cycle_task)

  def read_revisions(self):
    """Read revisions for Cycle Task object."""
    responses = []
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    for query in ["source_type={}&source_id={}",
                  "destination_type={}&destination_id={}",
                  "resource_type={}&resource_id={}"]:
      responses.append(
          self.api.get_query(
              all_models.CycleTaskGroupObjectTask,
              query.format("cycle_task_group_object_task", cycle_task.id)
          )
      )
    return responses

  def add_comment(self):
    """Map new comment to cycle task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.get(
        self.cycle_task_id
    )
    _, comment = self.objgen.generate_object(all_models.Comment, {
        "description": factories.random_str(),
        "context": None,
    })
    return self.objgen.generate_relationship(source=cycle_task,
                                             destination=comment)[0]

  def read_comment(self):
    """Read comments mapped to cycle task"""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.get(
        self.cycle_task_id
    )
    with factories.single_commit():
      comment = factories.CommentFactory(description=factories.random_str())
      factories.RelationshipFactory(source=cycle_task, destination=comment)

    query_request_data = [{
        "fields": [],
        "filters": {
            "expression": {
                "object_name": "CycleTaskGroupObjectTask",
                "op": {
                    "name": "relevant"
                },
                "ids": [cycle_task.id]
            }
        },
        "object_name": "Comment",
    }]

    response = self.api.send_request(
        self.api.client.post,
        data=query_request_data,
        api_link="/query"
    )
    return response

  def map_control(self):
    """Map Control on which user don't have any rights to Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    control = factories.ControlFactory()
    return self.objgen.generate_relationship(
        source=cycle_task,
        destination=control,
    )[0]

  def map_created_control(self):
    """Map Control that was created by user to Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    control = factories.ControlFactory()
    # pylint: disable=protected-access
    for acl in control._access_control_list:
      if acl.ac_role_id == self.admin_control_id:
        factories.AccessControlPersonFactory(
            person_id=self.user_id,
            ac_list=acl,
        )
    return self.objgen.generate_relationship(
        source=cycle_task,
        destination=control,
    )[0]

  def read_mapped_control(self):
    """Read Control object mapped to Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    with factories.single_commit():
      control = factories.ControlFactory()
      factories.RelationshipFactory(source=cycle_task, destination=control)
    return self.api.get(control, control.id)

  def upmap_control(self):
    """Unmap Control from Task Group."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    with factories.single_commit():
      control = factories.ControlFactory()
      rel = factories.RelationshipFactory(
          source=cycle_task, destination=control
      )
    return self.api.delete(rel)

  def start(self):
    """Start Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"status": "In Progress"})

  def end(self):
    """End Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"status": "Finished"})

  def verify(self):
    """Verify Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"status": "Verified"})

  def decline(self):
    """Decline Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"status": "Declined"})

  def deprecate(self):
    """Deprecate Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"status": "Deprecated"})

  def restore(self):
    """Restore Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.put(cycle_task, {"status": "Assigned"})

  def assign(self):
    """Assign Cycle Task."""
    with factories.single_commit():
      user_obj = factories.PersonFactory()
      permission_factories.UserRoleFactory(
          role=all_models.Role.query.filter_by(
              name="Reader"
          ).first(),
          person=user_obj
      )
    acl_role_obj = all_models.AccessControlRole.query.filter_by(
        object_type='Workflow',
    ).first()
    cycle_task = all_models.CycleTaskGroupObjectTask.query.get(
        self.cycle_task_id
    )
    return self.api.put(
        cycle_task,
        {
            "ac_role_id": acl_role_obj.id,
            "person": {"id": user_obj.id, "type": "Person"}
        }
    )

  def delete_comment(self):
    """Delete Comment related to Cycle Task object."""
    return self.api.delete(self.comment)

  def bulk_update(self):
    """Bulk update for Cycle Task."""
    cycle_task = all_models.CycleTaskGroupObjectTask.query.first()
    return self.api.patch(
        cycle_task,
        [{"id": self.cycle_task_id, "state": "In Progress"}]
    )
