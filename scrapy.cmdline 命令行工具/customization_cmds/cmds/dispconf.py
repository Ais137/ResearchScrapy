# Name: 自定义命令
# Date: 2022-09-25
# Author: Ais
# Desc: 


from scrapy.commands import ScrapyCommand


class Command(ScrapyCommand):

    def short_desc(self):
        return "display config"

    def run(self, args, opts):
        print("----------" * 5)
        print(f"[args]: {args}")
        print(f"[opts]: {opts}")
    
