# -*- coding: utf-8 -*-
#
#   @author 2019 Ludovic Taffin
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

#   Reporting plugin for INGInious
import os

import logging

import pymongo
import web

from inginious.frontend.pages.course_admin.utils import INGIniousAdminPage

""" A plugin that displays beautiful reporting widgets """

PATH_TO_PLUGIN = os.path.abspath(os.path.dirname(__file__))


def add_admin_menu(course):  # pylint: disable=unused-argument
    """ Add a menu for jplag analyze in the administration """
    return ('reporting/', '<i class="fa fa-bar-chart"></i>&nbsp; Reporting')


def init(plugin_manager, _, _2, config):
    """ Init the plugin """

    class ReportingPage(INGIniousAdminPage):
        """Page to allow user choose students and tasks from the course and then display a report diagram"""

        def GET(self, courseID):
            """GET REQUEST - Allows students and tasks selection"""
            self._logger = logging.getLogger("inginious.webapp.plugins.reporting")
            self._logger.info("Starting Reporting plugin")

            c = self.course_factory.get_course(courseID)
            users = sorted(list(
                self.user_manager.get_users_info(self.user_manager.get_course_registered_users(c, False)).items()),
                key=lambda k: k[1][0] if k[1] is not None else "")

            tasks = c.get_tasks()
            self._logger.info(users)
            self._logger.info(tasks)

            self._logger.info("Rendering selection page")
            return self.template_helper.get_custom_renderer(PATH_TO_PLUGIN + "/templates/").reporting_index(users,
                                                                                                            tasks, c)

        def POST(self, courseID):
            """POST REQUEST - Allows display of the diagram"""
            self._logger = logging.getLogger("inginious.webapp.plugins.reporting")
            dicgrade = {}
            student_ids = []
            task_ids = []
            evaluated_submissions = []
            x = web.input()

            def students_per_grade(grade_table):
                for grade in grade_table:
                    grade = float(grade) / 5
                    grade = round(grade * 2) * 0.5
                    dicgrade[grade] = 1 if grade not in dicgrade else dicgrade[grade] + 1
                return dicgrade

            for key in x:
                if key.startswith("student"):
                    student_ids.append(x[key])
                else:
                    task_ids.append(x[key])

            self._logger.info(student_ids)
            self._logger.info(task_ids)

            for stud_id in student_ids:
                for task_id in task_ids:
                    submissions = list(self.database.submissions.find(
                        {"courseid": courseID, "taskid": task_id, "username": stud_id}).sort(
                        [("submitted_on", pymongo.DESCENDING)]))
                    if len(submissions) > 0:
                        evaluated_submissions.append(submissions[0]["grade"])
                    else:
                        pass
            table_stud_per_grade = students_per_grade(evaluated_submissions)
            course = self.course_factory.get_course(courseID)
            return self.template_helper.get_custom_renderer(PATH_TO_PLUGIN + "/templates/") \
                .reporting_chart(course, table_stud_per_grade)

    plugin_manager.add_page("/admin/([^/]+)/reporting/", ReportingPage)
    plugin_manager.add_hook('course_admin_menu', add_admin_menu)
