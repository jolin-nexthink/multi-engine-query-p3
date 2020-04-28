"""Setup command line argument processor for multi_engine_query"""
from __future__ import print_function

# Native imports
import argparse

# Version string
__VERSION = '0.1'

def handle_args():
    _PROGRAM = 'multi-engine-query-p3'

    # Default set of option flags; all False
    _debug_default = {
        'engine': False,
        'general': False,
        'portal': False
        }

    # All flags enabled, for use with -d and no qualifiers
    _debug_all_enabled = {
        'engine': True,
        'general': True,
        'portal': True
        }

    # Default set of exclude flags; all False
    _exclude_default = {
        'file': False
        }

    # All flags enabled, for use with -x and no qualifiers
    _exclude_all_enabled = {
        'file': True
        }

    # Define class to help with formatting of the SplitArgsAction
    class CustomHelpFormatter(argparse.HelpFormatter):

        def _format_action(self, action):
            width = 24
            if type(action) == SplitDebugArgsAction:
                subcommand = '-d [OPTIONS]' # self._format_action_invocation(action) # type: str
                # format help line
                help_text =  'Enables adding debugging information to the log file by\n'
                help_text += '{:{width}}adding zero or more of the following character values\n'.format(' ', width=width)
                help_text += '{:{width}}after the -d command line argument:\n'.format(' ', width=width)
                help_text += '{:{width}}\te -- Include Engine information\n'.format(' ', width=width)
                help_text += '{:{width}}\tg -- Include General information\n'.format(' ', width=width)
                help_text += '{:{width}}\tp -- Include Portal information\n'.format(' ', width=width)
                help_text += '{:{width}}Specifying -d without any qualifiers, is the same as specifying all qualifiers\n'.format(' ', width=width)
                help_text += '{:{width}}For example:\n'.format(' ', width=width)
                help_text += '{:{width}}\t{program} -d e\n'.format(' ', width=width, program=_PROGRAM)
                help_text += '{:{width}}\t\tWill include Engine debug informaiton in the log.\n'.format(' ', width=width)
                help_text += '{:{width}}\t{program} -d\n'.format(' ', width=width, program=_PROGRAM)
                help_text += '{:{width}}\t\tIs equivalent to specifying "{program} -d egp".\n'.format(' ', width=width, program=_PROGRAM)
                return '\n  {:{width}}{}'.format(subcommand, help_text, width=width-2)
            elif type(action) == SplitExcludeArgsAction:
                subcommand = '-x [OPTIONS]' # self._format_action_invocation(action) # type: str
                # format help line
                help_text =  'Excludes the following operations from the script by\n'
                help_text += '{:{width}}adding zero or more of the following character values\n'.format(' ', width=width)
                help_text += '{:{width}}after the -x command line argument:\n'.format(' ', width=width)
                help_text += '{:{width}}\tf -- Exclude updates to any files\n'.format(' ', width=width)
                help_text += '{:{width}}Specifying -x without any qualifiers, is the same as specifying all qualifiers\n'.format(' ', width=width)
                help_text += '{:{width}}For example:\n'.format(' ', width=width)
                help_text += '{:{width}}\t{program} -x f\n'.format(' ', width=width, program=_PROGRAM)
                help_text += '{:{width}}\t\tWill exclude file updates.\n'.format(' ', width=width)
                help_text += '{:{width}}\t{program} -x\n'.format(' ', width=width, program=_PROGRAM)
                help_text += '{:{width}}\t\tIs equivalent to specifying "{program} -x f".\n'.format(' ', width=width, program=_PROGRAM)
                return '\n  {:{width}}{}\n'.format(subcommand, help_text, width=width-2)
            else:
                return '\n' + super(CustomHelpFormatter, self)._format_action(action)

    # Define class to handle the list of debug options
    class SplitDebugArgsAction(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            super(SplitDebugArgsAction, self).__init__(option_strings, dest, **kwargs)


        def __call__(self, parser, namespace, values, option_string=None):
            if len(values) == 0:
                print('-d specified without qualifiers, enabling all debug flags')
                setattr(namespace, self.dest, _debug_all_enabled)
            else:
                valid_flags = ['e', 'g', 'p']
                dict_object = getattr(namespace, self.dest, None) or _default
                attrs = [v for v in list(values.replace(',','')) if v]
                bad_attrs = []
                for a in attrs:
                    if a == 'e': dict_object['engine'] = True
                    elif a == 'g': dict_object['general'] = True
                    elif a == 'p': dict_object['portal'] = True
                    else:
                        bad_attrs.append(a)
                if len(bad_attrs) > 0:
                    raise(argparse.ArgumentError(self, (
                        'May only include one or more of the following letters: '
                        '{}; found {}'
                        ).format(''.join(valid_flags), ''.join(bad_attrs))))
                setattr(namespace, self.dest, dict_object)

    # Define class to handle the list of exclude options
    class SplitExcludeArgsAction(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            super(SplitExcludeArgsAction, self).__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            if len(values) == 0:
                print('-x specified without qualifiers, enabling all exclude flags')
                setattr(namespace, self.dest, _exclude_all_enabled)
            else:
                valid_flags = ['f']
                dict_object = getattr(namespace, self.dest, None) or _default
                attrs = [v for v in list(values.replace(',','')) if v]
                bad_attrs = []
                for a in attrs:
                    if a == 'f': dict_object['file'] = True
                    else:
                        bad_attrs.append(a)
                if len(bad_attrs) > 0:
                    raise(argparse.ArgumentError(self, (
                        'May only include one or more of the following letters: '
                        '{}; found {}'
                        ).format(''.join(valid_flags), ''.join(bad_attrs))))
                setattr(namespace, self.dest, dict_object)

    # Define argument parser
    parser = argparse.ArgumentParser(
        prog=_PROGRAM,
        description=(
            'Runs an NXQL Query on all engines and puts the '
            'results in a specific file\n'),
        formatter_class = CustomHelpFormatter
        )

    # Define the arguments
    parser.add_argument('--version', action='version', 
        version='%(prog)s '+__VERSION)
    parser.add_argument('-t', dest='query_type', required=True,
        choices=['s','g'],
        help=('Determines the type of query to look for. '
              'An "s" specifies a Single Named Query will be '
              'in the -n (name) argument. '
              'A "g" specifies that a Named Query Group will be '
              'in the -n (name) argument. In that case, all queries '
              'in that Named Group file will be executed.'),
        action='store')
    parser.add_argument('-n', dest='name', required=True,
        help=('The case-sensitive name of the Single named Query, '
              'or the Named Query Group to be executed.'),
        action='store')
    parser.add_argument('-i', dest='info',
        help='Include additional runtime information in the log',
        action='store_true')
    parser.add_argument('-d', dest='options', nargs='*',
        metavar=('[OPTIONS]'),
        default=_debug_default, action=SplitDebugArgsAction)
    parser.add_argument('-x', dest='exclude', nargs='*',
        metavar=('[OPTIONS]'),
        default=_exclude_default, action=SplitExcludeArgsAction)
    
    return parser.parse_args()

