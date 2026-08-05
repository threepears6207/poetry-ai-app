import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from database import (
    get_connection,
    initialize_database,
    resolve_db_path
)



# =========================
# 多诗库来源
# =========================

SOURCE_PATHS = [

    (
        BACKEND_DIR
        / "data_sources"
        / "classic_poems"
        / "tang_poems_candidates.json"
    )

]


ARRAY_FIELDS = (
    "content",
    "tags",
    "theme_tags",
    "knowledge_tags"
)



# =========================
# 读取JSON
# =========================

def load_json_file(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"诗库不存在:{path}"
        )


    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)



    if not isinstance(data,list):

        raise ValueError(
            f"{path.name}必须是JSON数组"
        )


    return data





# =========================
# 校验诗库
# =========================

def load_and_validate_poems():


    all_poems=[]



    for source_path in SOURCE_PATHS:


        poems = load_json_file(
            source_path
        )


        print(
            f"加载诗库:{source_path.name},数量:{len(poems)}"
        )


        all_poems.extend(
            poems
        )



    seen_ids=set()



    for index, poem in enumerate(
        all_poems,
        start=1
    ):


        poem_id=str(
            poem.get(
                "id",
                ""
            )
        ).strip()



        title=str(
            poem.get(
                "title",
                ""
            )
        ).strip()



        author=str(
            poem.get(
                "author",
                ""
            )
        ).strip()



        content=poem.get(
            "content"
        )



        if not poem_id or not title or not author:


            raise ValueError(
                f"第{index}首缺少 id/title/author"
            )



        if not isinstance(
            content,
            list
        ) or not content:


            raise ValueError(
                f"{poem_id} content格式错误"
            )



        # 只禁止ID重复
        if poem_id in seen_ids:


            raise ValueError(
                f"重复ID:{poem_id}"
            )



        for field in ARRAY_FIELDS:


            value = poem.get(
                field,
                []
            )


            if not isinstance(
                value,
                list
            ):


                raise ValueError(
                    f"{poem_id} {field}必须是数组"
                )



        difficulty = poem.get(
            "difficulty",
            1
        )


        if not isinstance(
            difficulty,
            int
        ):


            raise ValueError(
                f"{poem_id} difficulty错误"
            )



        seen_ids.add(
            poem_id
        )



    return all_poems





# =========================
# JSON字段处理
# =========================

def json_text(value):

    return json.dumps(
        value or [],
        ensure_ascii=False,
        separators=(",", ":")
    )
# =========================
# 导入数据库
# =========================

def import_poems(
        sync_existing=False
):


    poems = load_and_validate_poems()



    print(
        f"总诗库数量:{len(poems)}"
    )



    initialize_database()



    database_path = resolve_db_path()



    connection = get_connection(
        database_path
    )



    try:


        before_count = connection.execute(

            "SELECT COUNT(*) FROM poems"

        ).fetchone()[0]



        before_changes = (
            connection.total_changes
        )



        connection.execute(
            "BEGIN"
        )



        # =====================
        # 同步更新模式
        # =====================

        if sync_existing:


            sql = """

            INSERT INTO poems (

                id,
                title,
                author,
                dynasty,
                content_json,
                translation,
                tags_json,
                age_level,
                age_range,
                difficulty,
                theme_tags_json,
                knowledge_tags_json,
                recommend_reason

            )

            VALUES (

                ?,?,?,?,?,?,?,?,?,?,?,?,?

            )


            ON CONFLICT(id)

            DO UPDATE SET


                title=excluded.title,

                author=excluded.author,

                dynasty=excluded.dynasty,

                content_json=excluded.content_json,

                translation=excluded.translation,

                tags_json=excluded.tags_json,

                age_level=excluded.age_level,

                age_range=excluded.age_range,

                difficulty=excluded.difficulty,

                theme_tags_json=excluded.theme_tags_json,

                knowledge_tags_json=excluded.knowledge_tags_json,

                recommend_reason=excluded.recommend_reason

            """



        # =====================
        # 只新增模式
        # =====================

        else:


            sql = """

            INSERT OR IGNORE INTO poems (

                id,
                title,
                author,
                dynasty,
                content_json,
                translation,
                tags_json,
                age_level,
                age_range,
                difficulty,
                theme_tags_json,
                knowledge_tags_json,
                recommend_reason

            )

            VALUES (

                ?,?,?,?,?,?,?,?,?,?,?,?,?

            )

            """




        for poem in poems:


            connection.execute(

                sql,

                (

                    poem.get(
                        "id",
                        ""
                    ),


                    poem.get(
                        "title",
                        ""
                    ),


                    poem.get(
                        "author",
                        ""
                    ),


                    poem.get(
                        "dynasty",
                        ""
                    ),


                    json_text(
                        poem.get(
                            "content",
                            []
                        )
                    ),


                    poem.get(
                        "translation",
                        ""
                    ),


                    json_text(
                        poem.get(
                            "tags",
                            []
                        )
                    ),


                    poem.get(
                        "age_level",
                        ""
                    ),


                    poem.get(
                        "age_range",
                        ""
                    ),


                    poem.get(
                        "difficulty",
                        1
                    ),


                    json_text(
                        poem.get(
                            "theme_tags",
                            []
                        )
                    ),


                    json_text(
                        poem.get(
                            "knowledge_tags",
                            []
                        )
                    ),


                    poem.get(
                        "recommend_reason",
                        ""
                    )

                )

            )



        connection.commit()



        inserted_count = (

            connection.total_changes

            -

            before_changes

        )



        after_count = connection.execute(

            "SELECT COUNT(*) FROM poems"

        ).fetchone()[0]



        integrity_check = connection.execute(

            "PRAGMA integrity_check"

        ).fetchone()[0]



    except Exception:


        connection.rollback()

        raise



    finally:


        connection.close()



    return {


        "database_path":

            str(database_path),



        "source_files":

            [

                str(path)

                for path in SOURCE_PATHS

            ],



        "source_count":

            len(poems),



        "before_count":

            before_count,



        "inserted_count":

            inserted_count,



        "after_count":

            after_count,



        "integrity_check":

            integrity_check

    }





# =========================
# 命令入口
# =========================


if __name__ == "__main__":


    parser = argparse.ArgumentParser(

        description="导入多个古诗库到SQLite"

    )



    parser.add_argument(

        "--sync-existing",

        action="store_true",

        help="同步更新已有诗词"

    )



    args = parser.parse_args()



    result = import_poems(

        sync_existing=args.sync_existing

    )



    print(

        json.dumps(

            result,

            ensure_ascii=False,

            indent=2

        )

    )