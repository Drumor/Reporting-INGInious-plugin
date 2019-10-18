#!/usr/bin/env python
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
import json
import os

import logging

import pymongo
import web

from inginious.frontend.pages.course_admin.utils import INGIniousAdminPage

""" A plugin that displays beautiful reporting widgets """

PATH_TO_PLUGIN = os.path.abspath(os.path.dirname(__file__))


def add_admin_menu(course):  # pylint: disable=unused-argument
    """ Add a menu for jplag analyze in the administration """
    return 'reporting', '<i class="fa fa-bar-chart"></i>&nbsp; Reporting'





class StaticMockPage(object):
    # TODO: Replace by shared static middleware and let webserver serve the files
    def GET(self, path):
        if not os.path.abspath(PATH_TO_PLUGIN) in os.path.abspath(os.path.join(PATH_TO_PLUGIN, path)):
            raise web.notfound()

        try:
            with open(os.path.join(PATH_TO_PLUGIN, "static", path), 'rb') as file:
                return file.read()
        except:
            raise web.notfound()

    def POST(self, path):
        return self.GET(path)


def init(plugin_manager, _, _2, config):
    """ Init the plugin """

    def _clean_data(data):
        cleaned = data.replace("&#39;", "")
        cleaned = cleaned.replace("[", "")
        cleaned = cleaned.replace("]", "")
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.split(",")
        return cleaned

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

            self._logger.info("Rendering selection page")
            return self.template_helper.get_custom_renderer(PATH_TO_PLUGIN + "/templates/").reporting_index(users,
                                                                                                            tasks, c)

        def POST(self, courseID):
            """POST REQUEST - Allows display of the diagram"""
            self._logger = logging.getLogger("inginious.webapp.plugins.reporting")
            course = self.course_factory.get_course(courseID)
            student_ids = []
            task_ids = []
            x = web.input()
            for key in x:
                if key.startswith("student"):
                    student_ids.append(x[key])
                else:
                    task_ids.append(x[key])

            student_ids = (str(student_ids)).encode("ascii").decode()
            task_ids = ",".join(task_ids)
            return self.template_helper.get_custom_renderer(PATH_TO_PLUGIN + "/templates/") \
                .reporting_chart(course, student_ids, task_ids)

    class Diagram1Page(INGIniousAdminPage):
        def POST(self, courseID):
            self._logger = logging.getLogger("inginious.webapp.plugins.reporting")
            dicgrade = {}
            data = web.input()

            student_ids = _clean_data(data["student_ids"])
            task_ids = _clean_data(data["task_ids"])
            evaluated_submissions = {}

            def students_per_grade(grades_per_tasks):
                for key, value in grades_per_tasks.items():
                    dicgrade[key] = {}
                    for grade in value:
                        grade = float(grade) / 5
                        grade = round(grade * 2) * 0.5
                        if grade not in dicgrade[key]:
                            dicgrade[key][grade] = 1
                        else:
                            dicgrade[key][grade] = dicgrade[key][grade] + 1
                return dicgrade

            if student_ids == ['']:
                student_ids = (self.database.aggregations.find_one({"courseid": courseID}, {"students":1}))
                student_ids = student_ids["students"]
            for task_id in task_ids:
                evaluated_submissions[task_id] = []
                for stud_id in student_ids:
                    submissions = list(self.database.submissions.find(
                        {"courseid": courseID, "taskid": task_id, "username": stud_id}).sort(
                        [("submitted_on", pymongo.DESCENDING)]))
                    if len(submissions) > 0:
                        evaluated_submissions[task_id].append(submissions[0]["grade"])

            table_stud_per_grade = students_per_grade(evaluated_submissions)
            return json.dumps(table_stud_per_grade)

    class Diagram2Page(INGIniousAdminPage):
        def POST(self, courseID):
            course = self.course_factory.get_course(courseID)
            self._logger = logging.getLogger("inginious.webapp.plugins.reporting")
            data = web.input()
            task_ids = _clean_data(data["task_ids"])
            tasks_data = {}
            tasks_data["nstuds"] = len(self.user_manager.get_course_registered_users(course, False))
            for task_id in task_ids:
                data = list(self.database.user_tasks.aggregate(
                    [
                        {
                            "$match":
                                {
                                    "courseid": courseID,
                                    "taskid": task_id,
                                    "username": {"$in": self.user_manager.get_course_registered_users(course, False)}
                                }
                        },
                        {
                            "$group":
                                {
                                    "_id": "$taskid",
                                    "viewed": {"$sum": 1},
                                    "attempted": {"$sum": {"$cond": [{"$ne": ["$tried", 0]}, 1, 0]}},
                                    "succeeded": {"$sum": {"$cond": ["$succeeded", 1, 0]}}
                                }
                        }
                    ]))
                tasks_data[task_id] = data
            return json.dumps(tasks_data)

    plugin_manager.add_page('/plugins/reporting/static/(.+)', StaticMockPage)
    plugin_manager.add_hook("javascript_header", lambda: "/plugins/reporting/static/chartjs-plugin-annotation.min.js")
    plugin_manager.add_page("/admin/([^/]+)/reporting", ReportingPage)
    plugin_manager.add_page("/admin/([^/]+)/reporting/diag1", Diagram1Page)
    plugin_manager.add_page("/admin/([^/]+)/reporting/diag2", Diagram2Page)
    plugin_manager.add_hook('course_admin_menu', add_admin_menu)
