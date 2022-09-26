import re
import os
import string
from importlib.util import find_spec
from os.path import join, exists, abspath
from shutil import ignore_patterns, move, copy2, copystat
from stat import S_IWUSR as OWNER_WRITE_PERMISSION

import scrapy
from scrapy.commands import ScrapyCommand
from scrapy.utils.template import render_templatefile, string_camelcase
from scrapy.exceptions import UsageError


TEMPLATES_TO_RENDER = (
    ('scrapy.cfg',),
    ('${project_name}', 'settings.py.tmpl'),
    ('${project_name}', 'items.py.tmpl'),
    ('${project_name}', 'pipelines.py.tmpl'),
    ('${project_name}', 'middlewares.py.tmpl'),
)

IGNORE = ignore_patterns('*.pyc', '__pycache__', '.svn')

# 修改文件权限 
def _make_writable(path):
    current_permissions = os.stat(path).st_mode
    os.chmod(path, current_permissions | OWNER_WRITE_PERMISSION)


class Command(ScrapyCommand):

    requires_project = False
    default_settings = {'LOG_ENABLED': False,
                        'SPIDER_LOADER_WARN_ONLY': True}

    def syntax(self):
        return "<project_name> [project_dir]"

    def short_desc(self):
        return "Create new project"

    # 校验项目名的合法性
    def _is_valid_name(self, project_name):
        # 检测模块是否存在
        def _module_exists(module_name):
            spec = find_spec(module_name)
            return spec is not None and spec.loader is not None
        # 校验是否符合模式
        if not re.search(r'^[_a-zA-Z]\w*$', project_name):
            print('Error: Project names must begin with a letter and contain'
                  ' only\nletters, numbers and underscores')
        elif _module_exists(project_name):
            print(f'Error: Module {project_name!r} already exists')
        else:
            return True
        return False

    # 递归复制文件
    def _copytree(self, src, dst):
        """
        Since the original function always creates the directory, to resolve
        the issue a new function had to be created. It's a simple copy and
        was reduced for this case.

        More info at:
        https://github.com/scrapy/scrapy/pull/2005
        """
        ignore = IGNORE
        names = os.listdir(src)
        ignored_names = ignore(src, names)
        # 创建目标文件夹
        if not os.path.exists(dst):
            os.makedirs(dst)

        for name in names:
            # 跳过忽略文件
            if name in ignored_names:
                continue
            # 构建完整路径
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            # 递归复制目录
            if os.path.isdir(srcname):
                self._copytree(srcname, dstname)
            else:
                copy2(srcname, dstname)
                # 修改文件权限使其可写
                _make_writable(dstname)
        # Copy file metadata: 复制文件元数据
        copystat(src, dst)
        _make_writable(dst)

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

    # 模板文件目录: 通过配置文件的 TEMPLATES_DIR 参数设置
    @property
    def templates_dir(self):
        return join(
            self.settings['TEMPLATES_DIR'] or join(scrapy.__path__[0], 'templates'),
            'project'
        )
