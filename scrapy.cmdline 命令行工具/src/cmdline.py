"""  
scrapy命令行工具调用入口
"""

import sys
import os
import argparse
import cProfile
import inspect
import pkg_resources

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.commands import ScrapyCommand, ScrapyHelpFormatter
from scrapy.exceptions import UsageError
from scrapy.utils.misc import walk_modules
from scrapy.utils.project import inside_project, get_project_settings
from scrapy.utils.python import garbage_collect



class ScrapyArgumentParser(argparse.ArgumentParser):
    def _parse_optional(self, arg_string):
        # if starts with -: it means that is a parameter not a argument
        if arg_string[:2] == '-:':
            return None

        return super()._parse_optional(arg_string)


# 遍历指定模块下的所有 ScrapyCommand 子类
def _iter_command_classes(module_name):
    # TODO: add `name` attribute to commands and and merge this function with
    # scrapy.utils.spider.iter_spider_classes
    for module in walk_modules(module_name):
        for obj in vars(module).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, ScrapyCommand)
                and obj.__module__ == module.__name__
                and not obj == ScrapyCommand
            ):
                yield obj


# 获取ScrapyCommand对象映射表 -> {"模块名": "命令对象实例"}
def _get_commands_from_module(module, inproject):
    d = {}
    for cmd in _iter_command_classes(module):
        """  
        # 过滤条件
            1. 在项目内，查找到scrapy.cfg配置文件
            2. 或者该命令不需要配置文件
        # ScrapyCommand.requires_project 属性用于判断该命令是否依赖项目的配置文件
        """
        if inproject or not cmd.requires_project:
            cmdname = cmd.__module__.split('.')[-1]
            # 实例化对象 cmd -> Command(ScrapyCommand)
            d[cmdname] = cmd()
    return d # 


def _get_commands_from_entry_points(inproject, group='scrapy.commands'):
    cmds = {}
    for entry_point in pkg_resources.iter_entry_points(group):
        obj = entry_point.load()
        if inspect.isclass(obj):
            cmds[entry_point.name] = obj()
        else:
            raise Exception(f"Invalid entry point {entry_point.name}")
    return cmds


# 获取ScrapyCommand对象映射表 -> {"模块名": "命令对象实例"}
def _get_commands_dict(settings, inproject):
    # 从 scrapy.commands(默认模块) 加载命令对象
    cmds = _get_commands_from_module('scrapy.commands', inproject)
    cmds.update(_get_commands_from_entry_points(inproject))
    # 加载自定义命令行模块加载命令对象(scrapy.cfg:COMMANDS_MODULE)
    cmds_module = settings['COMMANDS_MODULE']
    if cmds_module:
        cmds.update(_get_commands_from_module(cmds_module, inproject))
    return cmds


def _pop_command_name(argv):
    i = 0
    for arg in argv[1:]:
        if not arg.startswith('-'):
            del argv[i]
            return arg
        i += 1


def _print_header(settings, inproject):
    version = scrapy.__version__
    if inproject:
        print(f"Scrapy {version} - project: {settings['BOT_NAME']}\n")
    else:
        print(f"Scrapy {version} - no active project\n")


def _print_commands(settings, inproject):
    _print_header(settings, inproject)
    print("Usage:")
    print("  scrapy <command> [options] [args]\n")
    print("Available commands:")
    cmds = _get_commands_dict(settings, inproject)
    for cmdname, cmdclass in sorted(cmds.items()):
        print(f"  {cmdname:<13} {cmdclass.short_desc()}")
    if not inproject:
        print()
        print("  [ more ]      More commands available when run from project directory")
    print()
    print('Use "scrapy <command> -h" to see more info about a command')


def _print_unknown_command(settings, cmdname, inproject):
    _print_header(settings, inproject)
    print(f"Unknown command: {cmdname}\n")
    print('Use "scrapy" to see available commands')


def _run_print_help(parser, func, *a, **kw):
    try:
        func(*a, **kw)
    except UsageError as e:
        if str(e):
            parser.error(str(e))
        if e.print_help:
            parser.print_help()
        sys.exit(2)

# 调用入口
def execute(argv=None, settings=None):
    if argv is None:
        argv = sys.argv
    # 获取项目的配置文件
    if settings is None:
        settings = get_project_settings()
        # set EDITOR from environment if available
        try:
            editor = os.environ['EDITOR']
        except KeyError:
            pass
        else:
            settings['EDITOR'] = editor
    # 向上遍历查找scrapy.cfg文件
    inproject = inside_project()
    # 获取命令行对象映射表
    # 加载默认命令模块[scrapy.commands]和自定义命令模块[scrapy.cfg:COMMANDS_MODULE]
    cmds = _get_commands_dict(settings, inproject)
    # 获取命令名
    cmdname = _pop_command_name(argv)
    if not cmdname:
        _print_commands(settings, inproject)
        sys.exit(0)
    elif cmdname not in cmds:
        _print_unknown_command(settings, cmdname, inproject)
        sys.exit(2)
    # 获取ScrapyCommand对象
    cmd = cmds[cmdname]
    # 解析命令
    parser = ScrapyArgumentParser(formatter_class=ScrapyHelpFormatter,
                                  usage=f"scrapy {cmdname} {cmd.syntax()}",
                                  conflict_handler='resolve',
                                  description=cmd.long_desc())
    # 设置配置数据
    settings.setdict(cmd.default_settings, priority='command')
    cmd.settings = settings
    cmd.add_options(parser)
    # 解析参数
    opts, args = parser.parse_known_args(args=argv[1:])
    # 执行 ScrapyCommand().process_options() 方法
    _run_print_help(parser, cmd.process_options, args, opts)
    # 执行 ScrapyCommand().run() 方法 -> 执行命令
    cmd.crawler_process = CrawlerProcess(settings)
    _run_print_help(parser, _run_command, cmd, args, opts)
    sys.exit(cmd.exitcode)


def _run_command(cmd, args, opts):
    if opts.profile:
        _run_command_profiled(cmd, args, opts)
    else:
        cmd.run(args, opts)


def _run_command_profiled(cmd, args, opts):
    if opts.profile:
        sys.stderr.write(f"scrapy: writing cProfile stats to {opts.profile!r}\n")
    loc = locals()
    # cProfile: 性能分析工具
    p = cProfile.Profile()
    p.runctx('cmd.run(args, opts)', globals(), loc)
    if opts.profile:
        p.dump_stats(opts.profile)


if __name__ == '__main__':
    try:
        execute()
    finally:
        # Twisted prints errors in DebugInfo.__del__, but PyPy does not run gc.collect() on exit:
        # http://doc.pypy.org/en/latest/cpython_differences.html
        # ?highlight=gc.collect#differences-related-to-garbage-collection-strategies
        garbage_collect()
