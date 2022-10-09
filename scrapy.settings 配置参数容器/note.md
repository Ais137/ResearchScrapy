# scrapy.settings 配置参数容器

## Overview · 概述
scrapy框架通过 *scrapy.settings.Settings* 对象来存储框架运行时所需要的配置参数。

--------------------------------------------------
## Source Code Analysis · 源码分析

### 1. scrapy框架配置参数的加载机制分析
通过对 *scrapy.cmdline* 命令行工具的源码分析可以发现。
在 *scrapy.cmdline.execute()* 中的以下代码片段中加载了配置参数 
```
def execute(argv=None, settings=None):
    ...
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
    ...
```
其中 *get_project_settings()* 函数用于获取当前项目的配置


### 2. [get_project_settings()](./src/utils/project.py) 函数实现
```
# 获取项目配置
def get_project_settings():
    # 检测环境变量中是否存在 SCRAPY_SETTINGS_MODULE 
    if ENVVAR not in os.environ:
        project = os.environ.get('SCRAPY_PROJECT', 'default')
        # 初始化环境参数
        # 1. 添加环境变量 SCRAPY_SETTINGS_MODULE, 存储配置文件路径(settings.py)
        # 2. 将项目路径添加到系统路径中(scrapy.cfg文件所在目录)
        init_env(project)

    # 构建配置对象 -> scrapy.settings.Settings
    settings = Settings()
    # 加载项目配置参数
    settings_module_path = os.environ.get(ENVVAR)
    if settings_module_path:
        settings.setmodule(settings_module_path, priority='project')

    # 遍历以 SCRAPY_ 开头的环境变量
    scrapy_envvars = {k[7:]: v for k, v in os.environ.items() if
                      k.startswith('SCRAPY_')}
    # 有效的scrapy环境变量
    valid_envvars = {
        'CHECK',
        'PROJECT',
        'PYTHON_SHELL',
        'SETTINGS_MODULE',
    }
    # 根据 valid_envvars 列表过滤无效的环境变量
    setting_envvars = {k for k in scrapy_envvars if k not in valid_envvars}
    if setting_envvars:
        setting_envvar_list = ', '.join(sorted(setting_envvars))
        warnings.warn(
            'Use of environment variables prefixed with SCRAPY_ to override '
            'settings is deprecated. The following environment variables are '
            f'currently defined: {setting_envvar_list}',
            ScrapyDeprecationWarning
        )
    # 加载环境变量到配置对象中
    settings.setdict(scrapy_envvars, priority='project')

    return settings
```
由上述源码可知，*get_project_settings()* 函数通过环境变量 **SCRAPY_SETTINGS_MODULE**
来查找项目的配置模块，并封装到 *Settings* 类中。其中在 *init_env* 函数中会对scrapy框架
运行所需的环境变量进行初始化。(具体实现位于 *scrapy.utils.conf.init_env* 中)。


### 3. 核心类 [scrapy.settings.Settings](./src/settings/__init__.py) 分析
*scrapy.settings.Settings* 类的源码位于 scrapy.settings.\_\_init\_\_.py
```
class Settings(BaseSettings):
    """
    This object stores Scrapy settings for the configuration of internal
    components, and can be used for any further customization.

    It is a direct subclass and supports all methods of
    :class:`~scrapy.settings.BaseSettings`. Additionally, after instantiation
    of this class, the new object will have the global default settings
    described on :ref:`topics-settings-ref` already populated.
    """

    def __init__(self, values=None, priority='project'):
        # Do not pass kwarg values here. We don't want to promote user-defined
        # dicts, and we want to update, not replace, default dicts with the
        # values given by the user
        super().__init__()
        # 填充默认配置
        self.setmodule(default_settings, 'default')
        # Promote default dictionaries to BaseSettings instances for per-key
        # priorities
        for name, val in self.items():
            # 将配置中的字典类型的值封装到BaseSettings对象中
            if isinstance(val, dict):
                self.set(name, BaseSettings(val, 'default'), 'default')
        # 更新值
        self.update(values, priority)

```
其是 *BaseSettings* 的子类，主要功能是在创建类时加载默认的配置，并根据传入参数更新配置。
```
self.setmodule(default_settings, 'default')
```
其中 [scrapy.settings.default_settings](./src/settings/default_settings.py) 模块存储了默认配置参数。


### 4. 基类 [scrapy.settings.BaseSettings](./src/settings/__init__.py) 的结构分析
*scrapy.settings.BaseSettings* 是配置参数的实际存储对象。其架构实现了一个类字典的存储结构，
但是在存储键值的时候，额外存储了 *priority* 属性来表示优先级。
所有的配置参数都以键值对的形式存储在 *self.attributes(dict)* 属性中。
```
attributes = {
    "k1": SettingsAttribute(value=v1, priority=0),
    "k2": SettingsAttribute(value=v2, priority=10),
    ...
    "kn": BaseSettings(value=vn, priority=20)
}
```
其中 *SettingsAttribute* 类是值的容器，其中的两个主要属性：
 * value(any): 存储实际的值
 * priority(int): 优先级
并且提供 *set(self, value, priority)* 方法用于设置值，但是要注意的是，
在调用 *set* 方法设置新值时，只有当优先级大于或等于当前优先级才可以覆盖。
```
def set(self, value, priority):
    """Sets value if priority is higher or equal than current priority."""
    # 当优先级大于或等于当前优先级才可以覆盖
    if priority >= self.priority:
        set new value
```

#### ----------- *BaseSettings.set()* -----------
*BaseSettings* 通过 *set* 方法来设置值。
```
def set(self, name, value, priority='project'):
    # 检测是否可变
    self._assert_mutability()
    # 获取优先级(str->int)
    priority = get_settings_priority(priority)
    # 设置值
    if name not in self:
        if isinstance(value, SettingsAttribute):
            self.attributes[name] = value
        else:
            self.attributes[name] = SettingsAttribute(value, priority)
    else:
        self.attributes[name].set(value, priority)
```
在设置值时，封装成 *SettingsAttribute* 进行存储。
同时提供了一个 *setmodule* 的方法，支持以模块的形式存储配置并导入。
在加载时，通过 *import_module* 动态导入模块，并遍历(dir)模块属性。 

#### ----------- *BaseSettings.update()* -----------
*BaseSettings* 通过 *update* 方法来更新值。
```
def update(self, values, priority='project'):
    self._assert_mutability()
    # 转化成字典
    if isinstance(values, str):
        values = json.loads(values)
    if values is not None:
        if isinstance(values, BaseSettings):
            for name, value in values.items():
                self.set(name, value, values.getpriority(name))
        else:
            for name, value in values.items():
                self.set(name, value, priority)
```
通过对上述源码观察发现，当 *values* 参数是字符串时，会尝试将其通过 *json* 格式化
字典后，进行遍历赋值。因此 *update* 方法可接受的参数包括 **str|dict|BaseSettings**,
更一般的，其支持实现了 *items()* 方法的一个可迭代对象。

需要注意的是，不管是 *set* 还是 *update* 方法，实际的值的存储操作是托管到
*SettingsAttribute.set()* 上进行的，因此只有当优先级大于或等于当前优先级才可以覆盖。

#### ----------- *BaseSettings.get()* -----------
*BaseSettings* 通过 *get* 方法来提供值的访问。
其中 *get* 方法用于获取值的 *原始值*, 其实现相当于访问 SettingsAttribute.value
```
def __getitem__(self, opt_name):
    if opt_name not in self:
        return None
    return self.attributes[opt_name].value
```
同时还提供了以下方法，对原始值的类型进行转换后返回:
 * getbool(): 布尔类型
 * getint(): 整型
 * getfloat(): 浮点数
 * getlist(): 列表
 * getdict(): 字典

### 5. 优先级表
在模块的 SETTINGS_PRIORITIES 属性中存储了优先级表。
```
SETTINGS_PRIORITIES = {
    'default': 0,
    'command': 10,
    'project': 20,
    'spider': 30,
    'cmdline': 40,
}
```
在实际的存储中，会通过调用 *get_settings_priority(priority)* 方法来获取优先级的整型值进行存储。同时支持通过整型来直接设置优先级。


### 6. Settings对象的配置参数加载流程分析
当使用 *scrapy crawl demo* 命令运行爬虫时，Settings对象的构建流程如下
1. scrapy.cmdline.execute() -> get_project_settings(): Settings类的实例化(priority=="default"), 加载默认配置参数(scrapy.settings.default_settings),  
    ```
    settings = Settings()
    ```
2. scrapy.cmdline.execute() -> get_project_settings(): 加载项目配置(priority=="project")
    ```
    settings_module_path = os.environ.get(ENVVAR)
    if settings_module_path:
        settings.setmodule(settings_module_path, priority='project')
    ```
3. scrapy.cmdline.execute(): 加载命令行子类中的默认配置(priority=="command")
    ```
    settings.setdict(cmd.default_settings, priority='command')
    ```
    需要注意的是，*cmd.default_settings* 中的 *default_settings* 属性是继承于 *ScrapyCommand* 类，如果该命令在项目内运行，由于优先级的原因(project>command), 会被项目配置所覆盖。

4. scrapy.crawler.Crawlaer.__init__(): 将当前配置更新到爬虫实例中(priority=="spider")
    ```
    self.spidercls.update_settings(self.settings)
    ```
    其中具体源码位于 *scrapy.spiders.Spider.update_settings()* 中
    ```
    @classmethod
    def update_settings(cls, settings):
        settings.setdict(cls.custom_settings or {}, priority='spider')
    ```
5. scrapy.cmdline.execute() -> scrapy.commands.ScrapyCommand.process_options(): 根据-s参数设置的配置参数进行覆盖(priority=="cmdline")
    ```
    def process_options(self, args, opts):
        ...
        self.settings.setdict(arglist_to_dict(opts.set), priority='cmdline')
        ...
    ```


--------------------------------------------------
## FrameWork · 架构
* [scrapy.settings.BaseSettings](./src/settings/__init__.py): 核心类，配置参数容器
* [scrapy.settings.default_settings](./src/settings/default_settings.py): 默认配置参数
* [scrapy.utils.project.get_project_settings](./src/utils/project.py): 获取当前项目配置


