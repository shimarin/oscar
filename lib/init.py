# -*- coding: utf-8 -*-
import os

import oscar

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="init")

def create_table(context):
    ## このtokenizerを使うと巨大なテキストを入れてサーチしたときに死ぬ
    tokenizer = "--default_tokenizer TokenBigramSplitSymbolAlphaDigit"
    #tokenizer = "--default_tokenizer TokenBigram"
    #tokenizer = ""
    commands = [
        # Fulltext(_key:md5 of original content,content:extract content)
        "table_create --name Fulltext --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table Fulltext --name title --flags COLUMN_SCALAR --type ShortText",
        "column_create --table Fulltext --name content --flags COLUMN_SCALAR --type LongText",

        # Files(_key:sha1 of path,path,name,fulltext=>Fulltext)
        "table_create --name Files --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table Files --name path --flags COLUMN_SCALAR --type ShortText",
        "column_create --table Files --name path_ft --flags COLUMN_SCALAR --type ShortText",
        "column_create --table Files --name name --flags COLUMN_SCALAR --type ShortText",
        "column_create --table Files --name fulltext --type Fulltext",
        "column_create --table Files --name mtime --type Time",
        "column_create --table Files --name size --type Int64",

        # Fulltext-to-file
        "column_create --table Fulltext --name file --flags COLUMN_INDEX --type Files --source fulltext",

        # Terms(fulltext_content:index of Fulltext.content)
        "table_create --name Terms --flags TABLE_PAT_KEY --key_type ShortText %s --normalizer NormalizerAuto" % tokenizer,
        "column_create --table Terms --name fulltext_title --flags COLUMN_INDEX|WITH_POSITION --type Fulltext --source title",
        "column_create --table Terms --name fulltext_content --flags COLUMN_INDEX|WITH_POSITION --type Fulltext --source content",
        "column_create --table Terms --name files_path --flags COLUMN_INDEX|WITH_POSITION --type Files --source path_ft",
        "column_create --table Terms --name files_name --flags COLUMN_INDEX|WITH_POSITION --type Files --source name",

        # Directory
        "table_create --name Directory --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table Directory --name name --flags COLUMN_SCALAR --type ShortText",
        "column_create --table Directory --name hash --flags COLUMN_SCALAR --type ShortText",

        # Paths(prefix:index of Files.path)
        "table_create --name Paths --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table Paths --name prefix --flags COLUMN_INDEX --type Files --source path",
        "column_create --table Paths --name dir_prefix --flags COLUMN_INDEX --type Directory --source name",

        # File queue
        "table_create --name FileQueue --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table FileQueue --name name --flags COLUMN_SCALAR --type ShortText",
        "column_create --table FileQueue --name size --flags COLUMN_SCALAR --type UInt64",

        # Directory queue
        "table_create --name DirectoryQueue --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table DirectoryQueue --name name --flags COLUMN_SCALAR --type ShortText",
        
        # Configuration
        "table_create --name Config --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table Config --name value --flags COLUMN_SCALAR --type ShortText",
        
        "table_create --name Log --flags TABLE_NO_KEY",
        "column_create --table Log --name time --type Time",
        "column_create --table Log --name category --type ShortText",
        "column_create --table Log --name content --type ShortText",
        
        "table_create --name LogTime --flags TABLE_PAT_KEY --key_type Int64",
        "column_create --table LogTime --name time --flags COLUMN_INDEX --type Log --source time",

        "table_create --name LogCategory --flags TABLE_PAT_KEY --key_type ShortText",
        "column_create --table LogCategory --name category --flags COLUMN_INDEX --type Log --source category"
    ]
    for command in commands:
        context.execute_command(command)

def init(base_dir):
    with oscar.context(base_dir, True) as context:
        create_table(context)

def run(args):
    for base_dir in args.base_dir:
        if not os.path.isdir(base_dir):
            oscar.log.error("'%s' does not exist or not a directory" % args.base_dir)
            return 1

        init(base_dir)
        oscar.log.info("Database %s initialized." % base_dir)
