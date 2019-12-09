# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Workflow RBAC Factory."""
from ggrc.models import all_models
from integration.ggrc import Api
from integration.ggrc.access_control.rbac_factories import base
from integration.ggrc.models import factories
from integration.ggrc_workflows.models import factories as wf_factories
from integration.ggrc_basic_permissions.models \
    import factories as permission_factories


class WorkflowRBACFactory(base.BaseRBACFactory):
  """Workflow RBAC factory class."""

  def __init__(self, user_id, acr, parent=None, authorization_user_id=None):
    """Set up objects for Workflow permission tests.

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
    """Create new Workflow object."""
    return self.api.post(all_models.Workflow, {
        "workflow": {
            "title": "New workflow",
            "context": None,
        }
    })

  def read(self):
    """Read existing Workflow object."""
    return self.api.get(all_models.Workflow, self.workflow_id)

  def update(self):
    """Update title of existing Workflow object."""
    workflow = all_models.Workflow.query.get(self.workflow_id)
    return self.api.put(workflow, {"title": factories.random_str()})

  def delete(self):
    """Delete Workflow object."""
    workflow = all_models.Workflow.query.get(self.workflow_id)
    return self.api.delete(workflow)

  def read_revisions(self):
    """Read revisions for Workflow object."""
    responses = []
    for query in ["source_type={}&source_id={}",
                  "destination_type={}&destination_id={}",
                  "resource_type={}&resource_id={}"]:
      responses.append(
          self.api.get_query(
              all_models.Workflow, query.format("workflow", self.workflow_id)
          )
      )
    return responses

  def clone(self):
    """Clone existing Workflow object."""
    with factories.single_commit():
      task_group = wf_factories.TaskGroupFactory(workflow_id=self.workflow_id)
      wf_factories.TaskGroupTaskFactory(task_group=task_group)

    return self.api.post(all_models.Workflow, {
        "workflow": {
            # workaround - title is required for validation
            "title": "",
            "clone": self.workflow_id,
            "clone_objects": True,
            "clone_people": True,
            "clone_tasks": True,
            "context": None,
        }
    })

  def activate(self):
    """Activate existing Workflow object"""
    workflow = all_models.Workflow.query.get(self.workflow_id)
    data = {
        "status": "Active",
        "recurrences": bool(workflow.repeat_every and workflow.unit)
    }
    return self.api.put(workflow, data)

  def assign_wf_role(self):
    """Assign WF role to Workflow object"""
    with factories.single_commit():
      user_obj = factories.PersonFactory()
      permission_factories.UserRoleFactory(
          role=all_models.Role.query.filter_by(
              name="Reader"
          ).first(),
          person=user_obj
      )
    acl_role = all_models.AccessControlRole.query.filter_by(
        object_type='Workflow',
        name='Admin'
    ).first()
    workflow = all_models.Workflow.query.get(self.workflow_id)
    return self.api.put(
        workflow,
        {
            "ac_role_id": acl_role.id,
            "person": {"id": user_obj.id, "type": "Person"}
        }
    )
