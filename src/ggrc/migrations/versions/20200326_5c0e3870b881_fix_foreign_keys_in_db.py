# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Fix foreign keys in DB

Create Date: 2020-03-26 18:18:51.695672
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op
from sqlalchemy import text
from ggrc.migrations import utils

revision = '5c0e3870b881'
down_revision = '51cadec32665'


def remove_invalid_user_roles():
  """Delete invalid user_roles rows with not existing people id"""
  connection = op.get_bind()
  person_sql = """
       SELECT r.id
       FROM user_roles AS r
       LEFT JOIN people AS p
           ON r.person_id = p.id
       WHERE (r.person_id IS NOT NULL AND p.id IS NULL)
   """
  persons = connection.execute(text(person_sql)).fetchall()
  person_ids = [o.id for o in persons]
  if person_ids:
    connection.execute(
        text("DELETE FROM user_roles WHERE id IN :person_ids"),
        person_ids=person_ids
    )
    utils.add_to_objects_without_revisions_bulk(
        connection, person_ids, "UserRole", "deleted"
    )


def remove_invalid_audit_firm_id():
  """Set null to audit_firm_id column for not existing value
  in org_groups table.
  """
  op.execute("""
    UPDATE `audits` audit
    LEFT JOIN `org_groups` AS org
    ON audit.audit_firm_id = org.id
    SET audit.audit_firm_id = NULL
    WHERE (audit.audit_firm_id IS NOT NULL AND org.id IS NULL);
  """)


def remove_invalid_risk_assesments():
  """Delete invalid risk_assesment rows with not existing programm id"""
  connection = op.get_bind()
  assessments_sql = """
       SELECT r.id
       FROM risk_assessments AS r
       LEFT JOIN programs AS p
           ON r.program_id = p.id
       WHERE (r.program_id IS NOT NULL AND p.id IS NULL)
   """
  assessments = connection.execute(text(assessments_sql)).fetchall()
  assessments_ids = [o.id for o in assessments]
  if assessments_ids:
    connection.execute(
        text("DELETE FROM risk_assessments WHERE id IN :assessments_ids"),
        assessments_ids=assessments_ids
    )
    utils.add_to_objects_without_revisions_bulk(
        connection, assessments_ids, "RiskAssessment", "deleted"
    )


def create_foreign_keys():
  """Create foreign keys"""
  op.execute("""
      ALTER TABLE `audits` ADD CONSTRAINT `fk_audit_firm_id`
      FOREIGN KEY (`audit_firm_id`)
      REFERENCES `org_groups` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `contexts` ADD CONSTRAINT `fk_contexts_contexts`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `custom_attribute_definitions` ADD CONSTRAINT
      `fk_custom_attribute_definitions_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `custom_attribute_values` ADD CONSTRAINT
      `fk_custom_attribute_values_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `cycle_task_groups` ADD CONSTRAINT
      `fk_secondary_contact_id`
      FOREIGN KEY (`secondary_contact_id`)
      REFERENCES `people` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `cycle_task_groups` ADD CONSTRAINT
      `fk_task_group_id`
      FOREIGN KEY (`task_group_id`)
      REFERENCES `task_groups` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `cycles` ADD CONSTRAINT
      `fk_cycles_secondary_contact_id`
      FOREIGN KEY (`secondary_contact_id`)
      REFERENCES `people` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `notification_types` ADD CONSTRAINT
      `fk_notification_types_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `notifications` ADD CONSTRAINT
      `fk_notifications_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `notifications_history` ADD CONSTRAINT
      `fk_notifications_history_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION
      """)
  op.execute("""
      ALTER TABLE `roles` ADD CONSTRAINT
      `fk_roles_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `saved_searches` ADD CONSTRAINT
      `fk_person_id`
      FOREIGN KEY (`person_id`)
      REFERENCES `people` (`id`)
      ON DELETE CASCADE""")
  op.execute("""
      ALTER TABLE `snapshots` ADD CONSTRAINT
      `fk_snapshots_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `task_groups` ADD CONSTRAINT
      `fk_task_groups_secondary_contact_id`
      FOREIGN KEY (`secondary_contact_id`)
      REFERENCES `people` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `threats` ADD CONSTRAINT
      `fk_threats_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `user_roles` ADD CONSTRAINT
      `fk_user_roles_person_id`
      FOREIGN KEY (`person_id`)
      REFERENCES `people` (`id`)
      ON DELETE NO ACTION""")
  op.execute("""
      ALTER TABLE `vendors` ADD CONSTRAINT
      `fk_vendors_context_id`
      FOREIGN KEY (`context_id`)
      REFERENCES `contexts` (`id`)
      ON DELETE NO ACTION""")


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  remove_invalid_audit_firm_id()
  remove_invalid_user_roles()
  remove_invalid_risk_assesments()
  create_foreign_keys()


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  raise NotImplementedError("Downgrade is not supported")
