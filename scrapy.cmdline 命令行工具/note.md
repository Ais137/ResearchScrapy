# scrapy.cmdline 命令行工具

## Overview · 概述
scrapy命令行工具封装了开发过程中的一些常用操作，比如项目构建，基准测试等。

--------------------------------------------------
## Source Code Analysis · 源码分析
### 1. 从 *scrapy startproject demo* 开始
上述命令用于创建scrapy项目的代码框架。其会在当前目录生下成一个 *demo* 目录，并包含一系列的模板代码。现在通过该命令来分析其源码实现和命令行工具的设计框架。

### 2. *startproject* 命令源码分析
*startproject* 命令的源码实现位于 [/commands/startproject.py](./src/commands/startproject.py)
核心逻辑在 *Command(ScrapyCommand)* 类的 *run* 方法中。
```
# (src): /scrapy/commands/startproject.py

def run(self, args, opts):
    
    # 检测参数数量[1, 2]
    if len(args) not in (1, 2):
        raise UsageError()

    # 调用参数: 项目名/项目目录
    project_name = args[0]
    project_dir = args[0]
    if len(args) == 2:
        project_dir = args[1]

    # 检查项目目录下是否包含scrapy.cfg文件
    if exists(join(project_dir, 'scrapy.cfg')):
        self.exitcode = 1
        print(f'Error: scrapy.cfg already exists in {abspath(project_dir)}')
        return

    # 检测项目名是否合法
    if not self._is_valid_name(project_name):
        self.exitcode = 1
        return

    # 复制模板文件到项目目录
    self._copytree(self.templates_dir, abspath(project_dir))

    # 修改模板文件的模块名(set:project_name)
    move(join(project_dir, 'module'), join(project_dir, project_name))

    # TEMPLATES_TO_RENDER -> 待渲染的模板文件列表
    for paths in TEMPLATES_TO_RENDER:
        # 拼接路径 -> '${project_name}/settings.py.tmpl'
        path = join(*paths)
        # 构建模板文件路径
        tplfile = join(project_dir, string.Template(path).substitute(project_name=project_name))
        # 渲染模板文件
        render_templatefile(tplfile, project_name=project_name, ProjectName=string_camelcase(project_name))

    # 输出
    print(f"New Scrapy project '{project_name}', using template directory "
            f"'{self.templates_dir}', created in:")
    print(f"    {abspath(project_dir)}\n")
    print("You can start your first spider with:")
    print(f"    cd {project_dir}")
    print("    scrapy genspider example example.com")

```
通过对上述源码分析发现，*startproject* 命令的主要功能与特性如下
* 主要功能: 将 **模板目录** 下的文件渲染后(值填充)复制到 **项目目录**。
* 默认的模板目录位于 [/templates/project/](./src/templates/project/scrapy.cfg)
* 可以通过在设置 **TEMPLATES_DIR** 参数来修改模板目录
* 当检测到项目目录下存在 *scrapy.cfg* 文件时会抛出异常。
* 通过指定可选参数(project_dir)来设置项目目录，否则默认项目目录为(./project_name/): -> scrapy startproject dome ./test/

### 3. 核心类 ScrapyCommand
通过对 scrapy.commands 下的子模块观察发现。大多数都是通过继承 *ScrapyCommand* 并重写 *run* 方法来实现主要功能。*ScrapyCommand* 的架构如下
```
# (src): /scrapy/commands/__init__.py

class ScrapyCommand:

    def __init__(self):
        self.settings = None  # set in scrapy.cmdline

    # 语法规则
    def syntax(self):
        """
        Command syntax (preferably one-line). Do not include command name.
        """
        return ""

    # 简述
    def short_desc(self):
        """
        A short description of the command
        """
        return ""

    # 详细描述
    def long_desc(self):
        """A long description of the command. Return short description when not
        available. It cannot contain newlines since contents will be formatted
        by optparser which removes newlines and wraps text.
        """
        return self.short_desc()

    # 帮助信息
    def help(self):
        """An extensive help for the command. It will be shown when using the
        "help" command. It can contain newlines since no post-formatting will
        be applied to its contents.
        """
        return self.long_desc()

    ······

    # 主要逻辑实现
    def run(self, args, opts):
        """
        Entry point for running commands
        """
        raise NotImplementedError

```

### 4. 命令行工具调用入口
知道了 *startproject* 命令的实现，现在来分析 scrapy 命令的调用入口。
通过对源码的观察可以发现，scrapy命令行工具的调用入口位于 [/scrapy/cmdline.py](./src/cmdline.py)
其核心代码如下:
```
# (src): /scrapy/cmdline.py

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

```
由上述源码可以分析出命令行工具的执行流程如下:
1. 获取项目的配置数据
2. 从当前目录向根目录遍历，查找 scrapy.cfg 文件
3. 遍历指定目录，构建命令行映射表 -> {模块名: Command(ScrapyCommand)对象}
    1. 首先从 scrapy.commands(默认模块) 加载
    2. 然后通过 *COMMANDS_MODULE* 参数加载自定义命令模块(继承ScrapyCommand的子类) 
```
# (src): /scrapy/cmdline.py

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
```
4. 解析命令并调用执行。

--------------------------------------------------
## FrameWork · 架构
通过对上述源码的分析，可以清楚的理解scrapy命令行工具的调用逻辑与架构设计。
* 通过 *scrapy.cmdline* 模块作为命令行工具的主调用入口。
* 在指定模块目录(默认目录为scrapy.commands)下遍历搜索继承 *ScrapyCommand* 的子类，并构建命令映射表。
* 根据输入参数调用指定命令映射表中实例的 *run* 方法并传入相关参数。

这种 *通过动态查找指定模块下的特定类，并提供统一调度入口的设计模式* 在我之前的一个项目
中也是这样设计的。当时的需求是，有N个脚本，需要设计一个调度器，通过任务API来执行相应的脚本。初步考虑是通过硬编码来设计一个映射表的方式将任务的执行器映射到对应的列表，但是这种设计的缺陷在于，在新增脚本的时候，需要同时向映射表中添加新的记录，如果忘记添加可能导致异常，同时调度器无法对脚本的结构有一个大致的了解。因此在实际的实现中，首先设计一个 *执行器* 基类，然后在子脚本中继承这个基类并在指定方法内实现具体的逻辑，在调度器构建时，通过扫描模块(importlib)下的指定子类，来实现调度执行功能。

--------------------------------------------------
## Extension · 扩展

### 添加自定义命令(./customization_cmds)
1. 构建自定义命令模块(cmds)
2. 添加子命令模块(dispconf)
3. 继承 *ScrapyCommand* 并实现 *run* 方法
4. 测试: > scrapy dispconf
PS: 该自定义命令只在 scrapy.cfg 目录及其子目录可见

### 使用自定义模板构建项目(./customization_templates)
1. 构建模板目录(./customization_templates/project)
2. 添加模板文件
3. 测试: scrapy startproject demo -s TEMPLATES_DIR=./customization_templates
