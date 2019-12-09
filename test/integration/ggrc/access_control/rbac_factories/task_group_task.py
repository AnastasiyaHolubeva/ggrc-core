# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Task Group Task RBAC Factory."""
from datetime import datetime

from ggrc.models import all_models
from integration.ggrc import Api
from integration.ggrc.access_control.rbac_factories import base
from integration.ggrc.models import factories
from integration.ggrc_basic_permissions.models \
    import factories as permission_factories


class TaskGroupTaskRBACFactory(base.BaseRBACFactory):
  """Task Group Task RBAC factory class."""

  def __init__(self, user_id, acr, parent=None, authorization_user_id=None):
    """Set up objects for Task Group Task permission tests.

    Args:
        user_id: Id of user under which scope objects will be created.
        acr: Instance of ACR that should be assigned for tested user.
        parent: Model name in scope of which objects should be set up.
        authorization_user_id: Id of user to authorization.
    """
    # pylint: disable=unused-argument
    self.setup_workflow_scope(user_id, acr)

    self.api = Api()

    self.setup_user(user_id, authorization_user_id)

  def create(self):
    """Create new Task Group Task object."""
    person = factories.PersonFactory()
    return self.api.post(all_models.TaskGroupTask, {
        "task_group_task": {
            "title": "New Task Group Task",
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "contact": person,
            "context": None,
            "task_group": {
                "id": self.task_group_id,
                "type": "Task Group",
            },
        }
    })

  def read(self):
    """Read existing Task Group Task object."""
    return self.api.get(all_models.TaskGroupTask, self.task_id)

  def update(self):
    """Update title of existing Task Group Task object."""
    task = all_models.TaskGroupTask.query.get(self.task_id)
    return self.api.put(task, {"title": factories.random_str()})

  def delete(self):
    """Delete Task Group Task object."""
    task = all_models.TaskGroupTask.query.get(self.task_id)
    return self.api.delete(task)

  def read_revisions(self):
    """Read revisions for Task Group Task object."""
    responses = []
    for query in ["source_type={}&source_id={}",
                  "destination_type={}&destination_id={}",
                  "resource_type={}&resource_id={}"]:
      responses.append(
          self.api.get_query(
              all_models.TaskGroupTask,
              query.format("task_group_task", self.task_id)
          )
      )
    return responses

  def assign(self):
    """Assign people to Task Group Task object"""
    with factories.single_commit():
      user = factories.PersonFactory()
      permission_factories.UserRoleFactory(
          role=all_models.Role.query.filter_by(
              name="Reader"
          ).first(),
          person=user
      )
    acl_role = all_models.AccessControlRole.query.filter_by(
        object_type='Workflow',
        name='Admin'
    ).first()
    task = all_models.TaskGroupTask.query.get(self.task_id)
    return self.api.put(
        task,
        {
            "ac_role_id": acl_role.id,
            "person": {"id": user.id, "type": "Person"}
        }
    )
