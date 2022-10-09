# scrapy框架配置参数解析

## TEMPLATES_DIR
* 功能: 代码模板目录，用于在 *scrapy startproject* 命令中创建代码模板时引用。
* 引用: **scrapy.commands.startproject.templates_dir()**
* 源码:
    ```
    @property
    def templates_dir(self):
        return join(
            self.settings['TEMPLATES_DIR'] or join(scrapy.__path__[0], 'templates'),
            'project'
        )
    ```

## COMMANDS_MODULE
* 功能: 命令行模块，用于加载自定义命令模块(继承ScrapyCommand的子类) 
* 引用: **scrapy.cmdline._get_commands_dict()**
* 源码:
    ```
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