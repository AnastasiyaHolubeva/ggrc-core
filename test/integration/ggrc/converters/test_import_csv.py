# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Tests for basic csv imports."""
import collections
from collections import OrderedDict

import ddt
import mock

from appengine import base
from ggrc import models
from ggrc.converters import errors
from ggrc.models import all_models
import ggrc_basic_permissions
from integration.ggrc import TestCase, api_helper
from integration.ggrc import generator
from integration.ggrc.models import factories
from integration.ggrc_basic_permissions.models \
    import factories as rbac_factories


@ddt.ddt
class TestBasicCsvImport(TestCase):
  """Test basic CSV imports."""
  # pylint: disable=too-many-public-methods

  def setUp(self):
    super(TestBasicCsvImport, self).setUp()
    self.generator = generator.ObjectGenerator()
    self.api = api_helper.Api()
    self.client.get("/login")

  def generate_policies(self):
    """Generate policy objects"""
    policy_data = [
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "Policy-{}".format(i)),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]) for i in range(3)
    ]
    response = self.import_data(*policy_data)
    return response

  def generate_objectives(self):
    """Generate Objective type objects"""
    objective_data = [
        collections.OrderedDict([
            ("object_type", "objective"),
            ("Code*", ""),
            ("title", "House of cards-{}".format(i)),
            ("admin", "user@example.com"),
            ("map:facility", "HOUSE-{}".format(i)),
        ]) for i in range(1, 5)
    ]
    response = self.import_data(*objective_data)
    return response

  def test_policy_basic_import(self):
    """Test basic policy import."""
    self.generate_policies()
    policies = models.Policy.query.count()
    self.assertEqual(policies, 3)
    revisions = models.Revision.query.filter(
        models.Revision.resource_type == "Policy"
    ).count()
    self.assertEqual(revisions, 3)
    policy = models.Policy.eager_query().first()
    self.assertEqual(policy.modified_by.email, "user@example.com")

  def test_policy_work_with_warnings(self):
    """Test Policy import with warnings."""
    def test_owners(policy):
      """Assert policy has the correct Admin set."""
      self.assertNotEqual([], policy.access_control_list)
      self.assertEqual(
          "user@example.com",
          policy.access_control_list[0][0].email
      )
      owner = models.Person.query.filter_by(email="user@example.com").first()
      self.assert_roles(policy, Admin=owner)

    self.import_data(collections.OrderedDict([
        ("object_type", "Policy"),
        ("Code*", ""),
        ("Title*", "Policy3"),
        ("Admin*", "user@example.com"),
        ("State*", "Draft"),
    ]))
    self.import_data(collections.OrderedDict([
        ("object_type", "Policy"),
        ("Code*", ""),
        ("Title*", "Policy4"),
        ("Admin*", "user@example.com"),
        ("State*", "Draft"),
    ]))
    policy3 = models.Policy.query.filter_by(title="Policy3").first()
    response = [
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", policy3.slug),
            ("Title*", "Policy3"),
            ("Admin", "miha@policy.com"),
            ("State*", "Draft"),
        ])
    ]
    response_json = self.import_data(*response)

    expected_warnings = {
        errors.UNKNOWN_USER_WARNING.format(line=3, email="miha@policy.com"),
        errors.OWNER_MISSING.format(line=3, column_name="Admin"),
    }
    response_warnings = response_json[0]["row_warnings"]
    self.assertEqual(expected_warnings, set(response_warnings))
    response_errors = response_json[0]["row_errors"]
    self.assertEqual(set(), set(response_errors))
    self.assertEqual(1, response_json[0]["updated"])

    policies = models.Policy.query.all()
    self.assertEqual(len(policies), 2)
    # Only 1 and 3 policies should have owners
    test_owners(policies[0])
    test_owners(policies[1])

  def test_policy_same_titles(self):
    """Test Policy imports with title collisions."""
    def test_owners(policy):
      """Assert policy has the correct Admin set."""
      self.assertNotEqual([], policy.access_control_list)
      self.assertEqual("user@example.com",
                       policy.access_control_list[0][0].email)
      owner = models.Person.query.filter_by(email="user@example.com").first()
      self.assert_roles(policy, Admin=owner)
    policy_template = [
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A different title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A different title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A different title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A totally different title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "A title"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ])
    ]

    response_json = self.import_data(*policy_template)
    self.assertEqual(3, response_json[0]["created"])
    self.assertEqual(6, response_json[0]["ignored"])
    self.assertEqual(0, response_json[0]["updated"])
    self.assertEqual(9, response_json[0]["rows"])

    expected_errors = {
        errors.DUPLICATE_VALUE_IN_CSV.format(
            line="4", processed_line="3", column_name="Title",
            value="A title"),
        errors.DUPLICATE_VALUE_IN_CSV.format(
            line="6", processed_line="3", column_name="Title",
            value="A title"),
        errors.DUPLICATE_VALUE_IN_CSV.format(
            line="10", processed_line="3", column_name="Title",
            value="A title"),
        errors.DUPLICATE_VALUE_IN_CSV.format(
            line="11", processed_line="3", column_name="Title",
            value="A title"),
        errors.DUPLICATE_VALUE_IN_CSV.format(
            line="7", processed_line="5", column_name="Title",
            value="A different title"),
        errors.DUPLICATE_VALUE_IN_CSV.format(
            line="8", processed_line="5", column_name="Title",
            value="A different title"),
    }
    response_errors = response_json[0]["row_errors"]
    self.assertEqual(expected_errors, set(response_errors))

    policies = models.Policy.query.all()
    self.assertEqual(len(policies), 3)
    for policy in policies:
      test_owners(policy)

  @ddt.data(['Standard', 'Regulation'],
            ['Standard', 'Policy'],
            ['Standard', 'Contract'],
            ['Standard', 'Requirement'],
            ['Regulation', 'Standard'],
            ['Regulation', 'Policy'],
            ['Regulation', 'Contract'],
            ['Regulation', 'Requirement'],
            ['Policy', 'Regulation'],
            ['Policy', 'Contract'],
            ['Policy', 'Requirement'],
            ['Policy', 'Standard'],
            ['Requirement', 'Regulation'],
            ['Requirement', 'Contract'],
            ['Requirement', 'Policy'],
            ['Requirement', 'Standard'],
            ['Contract', 'Requirement'],
            ['Contract', 'Contract'],
            ['Contract', 'Policy'],
            ['Contract', 'Standard'],
            )
  @ddt.unpack
  def test_map_core_objects(self, check_object, other_objects):
    """Ensure that core GRC objects correctly map to each other

    Core objects to test are:
    * Standard
    * Regulation
    * Policy
    * Requirement
    * Contract
    """
    obj = factories.get_model_factory(other_objects)

    # Create object
    new_object = obj(title='Test Title')
    data = [
        OrderedDict([
            ("object_type", check_object),
            ("Code*", ""),
            ("Title*", "{}-1".format(check_object)),
            ("Admin*", "user@example.com"),
            ("map:" + other_objects.lower(), new_object.slug)
        ])
    ]
    response = self.import_data(*data)
    self.assertEqual(response[0]["row_errors"], [])

  @ddt.data(['Standard', 'Standard', {"Standard": ["map:standard"]}],
            ['Policy', 'Policy', {"Policy": ["map:policy"]}],
            ['Contract', 'Contract', {"Contract": ["map:contract"]}],
            ['Requirement', 'Requirement', {}],
            ['Regulation', 'Regulation', {"Regulation": ["map:regulation"]}],
            ['Standard', 'Standard', {"Standard": ["map:standard"]}],
            )
  @ddt.unpack
  def test_map_core_objects_warnings(self, check_object, other_objects,
                                     block_warnings):
    """
    Test to check that the following pairs cannot be mapped:
    * Standard to Standard
    * Regulation to Regulation
    * Policy to Policy
    * Contract to Contract
    (however, Requirement CAN be mapped to Requirement)
    """
    obj = factories.get_model_factory(other_objects)

    # Create object
    new_object = obj(title='Test Title')
    data = [
        OrderedDict([
            ("object_type", check_object),
            ("Code*", ""),
            ("Title*", "{}-1".format(check_object)),
            ("Admin*", "user@example.com"),
            ("map:" + other_objects.lower(), new_object.slug)
        ])
    ]
    response = self.import_data(*data)

    self._check_csv_response(response, {
        obj_type: {
            "block_warnings": {
                errors.UNSUPPORTED_MAPPING.format(
                    line=2,
                    obj_a=obj_type,
                    obj_b=warn_column.split(":", 1)[1].title(),
                    column_name=warn_column
                )
            } for warn_column in warn_columns
        } for obj_type, warn_columns in block_warnings.iteritems()
    })

  def test_policy_unique_title(self):
    """Test import of existing policy."""
    policy_data = [
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "will this work"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ]),
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", ""),
            ("Title*", "will this work"),
            ("Admin*", "user@example.com"),
            ("State*", "Draft"),
        ])
    ]
    response_json = self.import_data(*policy_data)

    self.assertEqual(response_json[0]["row_errors"], [
        "Line 4 has the same Title 'will this work' as 3."
        " The line will be ignored."
    ])

  def test_assessments_import_update(self):
    """Test for updating Assessment with import

    Checks for fields being updated correctly
    """
    factories.PersonFactory(name="Anze",
                            email="anze@reciprocitylabs.com")
    factories.PersonFactory(name="Albert",
                            email="albert@reciprocitylabs.com")
    factories.AuditFactory(slug="AUDIT-Consolidated")
    audit1 = factories.AuditFactory(slug="AUDIT-Test")

    self.import_data(collections.OrderedDict([
        ("object_type", "Assessment"),
        ("Code*", ""),
        ("Audit", audit1.slug),
        ("Title", "PCI 1.1 Firewall and Router Configuration assessment"),
        ("Creators", "anze@reciprocitylabs.com"),
        ("Assignees", "anze@reciprocitylabs.com"),
        ("State", "Not Started"),
        ("Conclusion: Design", "Effective"),
        ("Conclusion: Operation", "Effective"),
    ]),
        collections.OrderedDict([
            ("object_type", "Assessment"),
            ("Code*", ""),
            ("Audit", audit1.slug),
            ("Title", "PCI 1.2 Firewall and Router Connections Configuration"),
            ("Creators", "anze@reciprocitylabs.com"),
            ("Assignees", "anze@reciprocitylabs.com"),
            ("State", "Not Started"),
            ("Conclusion: Design", "Effective"),
            ("Conclusion: Operation", "Effective"),
        ]))

    assessment = models.Assessment.query.filter_by(
        title="PCI 1.1 Firewall and Router Configuration assessment").first()
    audit = models.Audit.query.filter_by(slug="AUDIT-Consolidated").first()
    self.assertEqual(assessment.design, "Effective")
    self.assertEqual(assessment.operationally, "Effective")
    self.assertIsNone(models.Relationship.find_related(assessment, audit))

    assessment = models.Assessment.query.filter_by(
        title="PCI 1.2 Firewall and Router Connections Configuration").first()
    slug = assessment.slug
    audit_slug = audit.slug
    aud_data = collections.OrderedDict([
        ("object_type", "Assessment"),
        ("Code*", slug),
        ("Audit", audit_slug),
        ("Title", "PCI 1.1 Firewall and Router Connections Configuration"),
        ("Creators", "albert@reciprocitylabs.com"),
        ("Assignees", "albert@reciprocitylabs.com"),
        ("State", "Not Started"),
        ("Conclusion: Design", "Needs improvement"),
        ("Conclusion: Operation", "Ineffective"),
    ])
    response = self.import_data(aud_data)
    self._check_csv_response(response, {
        "Assessment": {
            "row_warnings": {
                errors.UNMODIFIABLE_COLUMN.format(line=3, column_name="Audit")
            }
        }
    })

    assessment = models.Assessment.query.filter_by(slug=slug).first()
    audit = models.Audit.query.filter_by(slug=audit_slug).first()
    self.assertEqual(assessment.design, "Needs improvement")
    self.assertEqual(assessment.operationally, "Ineffective")
    self.assertIsNone(models.Relationship.find_related(assessment, audit))

  def test_person_imports(self):
    """Test imports for Person object with user roles."""
    no_name = [
        collections.OrderedDict([
            ("object_type", "Person"),
            ("Name*", ""),
            ("Email", "user14@example.com"),
            ("Role", "Administrator"),
        ]),
    ]
    no_name_data = self.import_data(*no_name)
    expected_errors = {
        errors.MISSING_VALUE_ERROR.format(line=3, column_name="Name")}
    self.assertEqual(expected_errors, set(no_name_data[0]["row_errors"]))

    bad_email = [
        collections.OrderedDict([
            ("object_type", "Person"),
            ("Name*", "bad emil"),
            ("Email", "bad email dot com"),
        ]),
    ]
    bad_email_data = self.import_data(*bad_email)
    expected_errors = {
        errors.WRONG_VALUE_ERROR.format(line=3, column_name="Email")}
    self.assertEqual(expected_errors, set(bad_email_data[0]["row_errors"]))

    self.assertEqual(0, models.Person.query.filter_by(email=None).count())

  def test_duplicate_people(self):
    """Test adding two of the same object people objects in the same row."""
    user_data = [
        collections.OrderedDict([
            ("object_type", "Person"),
            ("name", "TestUser"),
            ("email", "user@example.com"),
        ]),
        collections.OrderedDict([
            ("object_type", "Person"),
            ("name", "TestUser2"),
            ("email", "user@example.com"),
        ]),
    ]

    response = self.import_data(*user_data)

    self.assertEqual(0, len(response[0]["row_warnings"]))
    self.assertEqual(1, len(response[0]["row_errors"]))

  def test_duplicate_people_objective(self):
    """Test duplicate error that causes request to fail."""
    self.generator.generate_object(models.Objective, {"slug": "objective1"})

    program_data = [
        collections.OrderedDict([
            ("object_type", "Program"),
            ("Title", "TestUser"),
            ("Code", ""),
            ("Program Managers", "user@example.com"),
        ]),
        collections.OrderedDict([
            ("object_type", "Program"),
            ("Title", "TestUser2"),
            ("Code", ""),
            ("Program Managers", "user@example.com"),
            ("map:objective", "objective1"),
        ]),
    ]
    response = self.import_data(*program_data)

    self.assertEqual(0, len(response[0]["row_warnings"]))
    self.assertEqual(0, len(response[0]["row_errors"]))

  def test_audit_import_context(self):
    """Test audit context on edits via import."""
    factories.ProgramFactory(slug="p")
    response = self.import_data(OrderedDict([
        ("object_type", "Audit"),
        ("Code*", ""),
        ("title", "audit"),
        ("Audit Captains", "user@example.com"),
        ("state", "In Progress"),
        ("program", "P"),
    ]))
    self._check_csv_response(response, {})

    audit = models.Audit.query.first()
    slug = audit.slug
    program = models.Program.query.first()
    self.assertNotEqual(audit.context_id, program.context_id)

    response = self.import_data(OrderedDict([
        ("object_type", "Audit"),
        ("Code*", slug),
        ("title", "audit"),
        ("Audit Captains", "user@example.com"),
        ("state", "In Progress"),
        ("program", "P"),
    ]))
    self._check_csv_response(response, {})

    audit = models.Audit.query.first()
    program = models.Program.query.first()
    self.assertNotEqual(audit.context_id, program.context_id)

  def test_import_with_code_column(self):
    """Test import csv with 'Code' column."""
    program_data = [
        collections.OrderedDict([
            ("object_type", "Program"),
            ("Title", "TestUser2345678"),
            ("Code", "program-1"),
            ("Program Managers", "user@example.com"),
        ])
    ]
    response = self.import_data(*program_data)

    self.assertEqual(response[0]["created"], 1)
    self.assertEqual(response[0]["block_errors"], [])

  def test_import_without_code_column(self):
    """Test error message when trying to import csv without 'Code' column."""
    program_data = [
        collections.OrderedDict([
            ("object_type", "Program"),
            ("Title", "TestUser2345678"),
            ("Program Managers", "user@example.com"),
        ])
    ]
    response = self.import_data(*program_data)

    self.assertEqual(response[0]["created"], 0)
    self.assertEqual(response[0]["block_errors"], [
        errors.MISSING_COLUMN.format(column_names="Code", line=2, s="")
    ])

  def test_import_code_validation(self):
    """Test validation of 'Code' column during import"""
    response = self.import_data(OrderedDict([
        ("object_type", "Program"),
        ("Code*", "*program-1"),
        ("Program managers", "user@example.com"),
        ("Title", "program-1"),
    ]))
    self._check_csv_response(response, {
        "Program": {
            "row_errors": {
                "Line 3: Field 'Code' validation failed with the following "
                "reason: Field 'Code' contains unsupported symbol '*'. "
                "The line will be ignored."
            }
        }
    })

  def test_import_lines(self):
    """Test importing CSV with empty lines in block
    and check correct lines numbering"""
    file_name = "import_empty_lines.csv"
    response = self.import_file(file_name, safe=False)
    expected = {
        "Program": {
            "created": 2,
            "row_errors": [],
            "row_warnings": [],
            "rows": 2,
        }
    }
    self._check_csv_response(response, expected)

  def test_import_hook_error(self):
    """Test errors in import"""
    with mock.patch(
        "ggrc.converters.base_block."
        "ImportBlockConverter.send_collection_post_signals",
        side_effect=Exception("Test Error")
    ):
      self._import_file("assessment_template_no_warnings.csv")
      self._import_file("assessment_with_templates.csv")
    self.assertEqual(models.all_models.Assessment.query.count(), 0)
    self.assertEqual(models.all_models.Revision.query.count(), 0)

  def test_import_object_with_folder(self):
    """Test checks to add folder via import"""
    folder_id = '1WXB8oulc68ZWdFhX96Tv1PBLi8iwALR3'
    response = self.import_data(OrderedDict([
        ("object_type", "Program"),
        ("Code*", ""),
        ("Program managers", "user@example.com"),
        ("Title", "program-1"),
        ("GDrive Folder ID", folder_id)

    ]))
    self._check_csv_response(response, {})
    program = models.Program.query.first()
    self.assertEqual(program.folder, folder_id)

  @ddt.data(
      'Contract',
      'Objective',
      'Policy',
      'Regulation',
      'Requirement',
      'Standard',
      'Threat',
  )
  def test_document_recipients(self, object_type):
    """Test check admin recipients for document created via import"""
    title = 'program 1'
    response = self.import_data(OrderedDict([
        ("object_type", object_type),
        ("Code*", ""),
        ("title", title),
        ("Admin", "user@example.com"),
        ("reference url", "http://someurl.html")
    ]))

    self._check_csv_response(response, {})
    document = all_models.Document.query.one()
    self.assertEqual(document.recipients, 'Admin')

  def test_document_recipients_issue(self):
    """Test check admin recipients for document created via import issue"""
    title = 'program 1'
    response = self.import_data(OrderedDict([
        ("object_type", 'Issue'),
        ("Code*", ""),
        ("title", title),
        ("Admin", "user@example.com"),
        ("reference url", "http://someurl.html"),
        ("Due Date", "07/30/2019")
    ]))

    self._check_csv_response(response, {})
    document = all_models.Document.query.one()
    self.assertEqual(document.recipients, 'Admin')


@base.with_memcache
class TestImportPermissions(TestCase):
  """Test permissions loading during import."""

  def setUp(self):
    super(TestImportPermissions, self).setUp()
    self.api = api_helper.Api()
    self.user = factories.PersonFactory()

  def test_import_permissions(self):
    """Test that permissions aren't recalculated during import new objects."""
    with factories.single_commit():
      audit = factories.AuditFactory(slug="audit-1")
      market = factories.MarketFactory()
      system_role = all_models.Role.query.filter(
          all_models.Role.name == "Creator"
      ).one()
      rbac_factories.UserRoleFactory(role=system_role, person=self.user)
      audit.add_person_with_role_name(self.user, "Audit Captains")
      market.add_person_with_role_name(self.user, "Admin")
    self._create_snapshots(audit, [market])

    data = [
        collections.OrderedDict([
            ("Code*", ""),
            ("Audit*", "audit-1"),
            ("Title*", "assessment{}".format(i)),
            ("State", "Not Started"),
            ("Assignees*", "user@example.com"),
            ("Creators*", "user@example.com"),
            ("map:market versions", market.slug),
        ]) for i in range(10)
    ]

    self.api.set_user(self.user)

    with mock.patch(
        "ggrc_basic_permissions.load_access_control_list",
        side_effect=ggrc_basic_permissions.load_access_control_list
    ) as acl_loader:
      response = self.api.run_import_job(self.user, "Assessment", data)
      self.assert200(response)
      # 10 Assessments should be created in import
      self.assertEqual(all_models.Assessment.query.count(), 10)
      # Permissions were loaded once on dry run and once on real run
      self.assertEqual(acl_loader.call_count, 2)

  def test_permissions_cleared(self):
    """Test that permissions where cleared after import."""
    with factories.single_commit():
      self.user = factories.PersonFactory()
      user_id = self.user.id
      market = factories.MarketFactory(slug="test market")
      system_role = all_models.Role.query.filter(
          all_models.Role.name == "Creator"
      ).one()
      rbac_factories.UserRoleFactory(role=system_role, person=self.user)
      market.add_person_with_role_name(self.user, "Admin")

    user_perm_key = 'permissions:{}'.format(user_id)

    # Recalculate permissions under new user
    self.api.set_user(self.user)
    self.api.client.get("/permissions")

    perm_ids = self.memcache_client.get('permissions:list')
    self.assertEqual(perm_ids, {user_perm_key})
    user_perm = self.memcache_client.get(user_perm_key)
    self.assertIsNotNone(user_perm)

    data = [
        collections.OrderedDict([
            ("Code*", ""),
            ("Title*", "Test Objective"),
            ("Admin", "user@example.com"),
            ("map:market", "test market"),
        ])
    ]
    response = self.api.run_import_job(self.user, "Objective", data)
    self.assert200(response)
    self.assertEqual(all_models.Objective.query.count(), 1)

    perm_ids = self.memcache_client.get('permissions:list')
    self.assertEqual(perm_ids, set())
    user_perm = self.memcache_client.get(user_perm_key)
    self.assertIsNone(user_perm)

  def test_import_without_code_object(self):
    """Test import csv without 'Code' but with existing title."""
    title = 'program 1'
    factories.ProgramFactory(title=title)
    self.assertEqual(len(models.Program.query.all()), 1)
    response = self.import_data(OrderedDict([
        ("object_type", "Program"),
        ("Code*", ""),
        ("title", title),
        ("Program managers", "user@example.com"),
    ]))

    expected_errors = {
        "Program": {
            "row_errors": {
                errors.DUPLICATE_VALUE.format(
                    line=3, column_name='title', value=title
                ),
            }
        }
    }
    self._check_csv_response(response, expected_errors)
    self.assertEqual(len(models.Program.query.all()), 1)
