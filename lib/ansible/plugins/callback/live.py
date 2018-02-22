# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    callback: live
    type: stdout
    short_description: screen output for solo mode
    version_added: historical
    description:
        - Solo mode with live stdout for raw and script tasks with fallback to minimal
'''

from ansible.plugins.callback import CallbackBase
from ansible import constants as C
import json


class CallbackModule(CallbackBase):

    '''
    This is the default callback interface, which simply prints messages
    to stdout when new callback events are received.
    '''

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'live'

    # name for this tasks can be generated from free_form
    FREE_FORM_MODULES = ('raw', 'script', 'command', 'shell')
    #ERROR! this task 'debug' has extra params, which is only allowed in the following modules: command, win_command, shell, win_shell, script, include, include_vars, include_tasks, include_role, import_tasks, import_role, add_host, group_by, set_fact, raw, meta

    def __init__(self):
        super(CallbackModule, self).__init__()
        self._play = None

    def _task_header(self, task, msg):
        name = task.name
        if not name:
            if task.action in self.FREE_FORM_MODULES:
                name = task.args['_raw_params']
                if len(name) > 25 :
                    name = '%s...' % task.args['_raw_params'][0:22]

        return u'%s [%s] %s' % (task.action, name, msg)

    def _display_command_generic_msg(self, task, result, caption, color):
        ''' output the result of a command run '''

        self._display.display("%s | rc=%s >>" % (self._task_header(task, caption), result.get('rc', -1)), color)
        # prevent dublication in case of live_stdout
        if not result.get('live_stdout', False):
            self._display.display("stdout was:", color=C.COLOR_HIGHLIGHT)
            self._display.display(result.get('stdout', ''))
        stderr = result.get('stderr', '')
        if stderr:
            self._display.display("stderr was:", color=C.COLOR_HIGHLIGHT)
            self._display.display(stderr, color=C.COLOR_ERROR)


    def _display_debug_msg(self, task, result):
        color = C.COLOR_OK
        if task.args.get('msg'):
            self._display.display("debug msg", color=C.COLOR_HIGHLIGHT)
            self._display.display(result.get('msg', ''), color)
        if task.args.get('var'):
            self._display.display("debug var \'%s\'" % task.args.get('var'), color=C.COLOR_HIGHLIGHT)
            text = result.get(task.args.get('var'), '')
            if 'IS NOT DEFINED' in text:
                color = C.COLOR_ERROR
                path = task.get_path()
                if path:
                    self._display.display(u"task path: %s" % path, color=C.COLOR_DEBUG)
            self._display.display(text, color)

        self._display.v(json.dumps(result))

        #if self._display.verbosity >= 2:

    #def _package_generic_msg(self, task, result)

    def v2_playbook_on_play_start(self, play):
        self._play = play

    # command [copy artifacts] started
    # stdout
    # ...
    # command [copy artifacts] OK/FAILED/CHANGED
    # STDERR:  if failed
    # ...
    #
    def v2_playbook_on_task_start(self, task, is_conditional):
        self._display.vvv("    v2_playbook_on_task_start")
        self._display.vvvvvv(json.dumps(task.args))

        if task.action == 'debug':
            return

        if self._play.strategy != 'free':
            self._display.display(self._task_header(task, "started"), color=C.COLOR_HIGHLIGHT)



    def v2_runner_on_ok(self, result):
        self._display.vvv("    v2_runner_on_OK")
        self._clean_results(result._result, result._task.action)
        self._handle_warnings(result._result)

        task = result._task

        #print(result._host.serialize())
        #self._display.display(json.dumps(result._host.serialize()), color=C.COLOR_DEBUG)

        if task.action == 'debug':
            self._display_debug_msg(result._task, result._result)
        elif task.action in self.FREE_FORM_MODULES:
            self._display_command_generic_msg(result._task, result._result, "SUCCESS", C.COLOR_OK)
        else:
            if 'changed' in result._result and result._result['changed']:
                #self._display.display(self._task_header(task, "OK")"%s | SUCCESS => %s" % (result._host.get_name(), self._dump_results(result._result, indent=4)), color=C.COLOR_CHANGED)
                self._display.display("%s | SUCCESS => %s" % (result._host.get_name(), self._dump_results(result._result, indent=4)), color=C.COLOR_CHANGED)
            else:
                self._display.display("%s | SUCCESS => %s" % (result._host.get_name(), self._dump_results(result._result, indent=4)), color=C.COLOR_OK)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._display.vvv("    v2_runner_on_failed")

        self._handle_exception(result._result)
        self._handle_warnings(result._result)

        task = result._task

        if task.action in self.FREE_FORM_MODULES:
            self._display_command_generic_msg(result._task, result._result, "FAILED", C.COLOR_ERROR)
        elif result._task.action in C.MODULE_NO_JSON and 'module_stderr' not in result._result:
            self._display.display(self._command_generic_msg(result._host.get_name(), result._result, "FAILED"), color=C.COLOR_ERROR)
        else:
            self._display.display("%s | FAILED! => %s" % (result._host.get_name(), self._dump_results(result._result, indent=4)), color=C.COLOR_ERROR)


    def v2_runner_on_skipped(self, result):
        self._display.display("%s | SKIPPED" % (result._host.get_name()), color=C.COLOR_SKIP)

    def v2_runner_on_unreachable(self, result):
        self._display.display("%s | UNREACHABLE! => %s" % (result._host.get_name(), self._dump_results(result._result, indent=4)), color=C.COLOR_UNREACHABLE)

    def v2_on_file_diff(self, result):
        if 'diff' in result._result and result._result['diff']:
            self._display.display(self._get_diff(result._result['diff']))
