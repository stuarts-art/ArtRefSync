import os
from typing import List, Optional
from sqlalchemy import Engine
from sqlmodel import Field, Relationship, SQLModel, ARRAY, Session, String, create_engine
from artrefsync.utils.PyInstallerUtils import resource_path

from artrefsync.config import config
from artrefsync.constants import BOARD, TABLE, APP

def main():
    with get_session() as session:
        tags = []
        # tag = Tag(id = "Test Tag")
        for i in range(100):
            tags.append(Tag(id=f"Test Tag {i}"))
        session.add_all(tags)
        # session.add(tag)
        session.commit()

# Singleton Engine
engine:Engine = None

def get_engine(db_dir = "db", db_name = "database.db") -> Engine:
    if db_dir:
        os.makedirs(resource_path(db_dir), exist_ok=True)
        db_name = resource_path(os.path.join(db_dir, db_name))
    else:
        db_name = resource_path(db_name)
    sql_name = f"sqlite:///{db_name.replace("\\", "/")}"
    print(sql_name)
    engine = create_engine(sql_name, echo=True)
    SQLModel.metadata.create_all(engine)
    engine.echo = False
    return engine


def get_session() -> Session:
    global engine
    if not engine:
        # db_name = "tagapp.db"
        db_dir = config[TABLE.APP][APP.DB_DIR]
        db_name = config[TABLE.APP][APP.DB_FILE_NAME]
        db_name = "tagapp_testing.db"
        engine = get_engine(db_dir, db_name)
    return Session(engine)

class PostTagLink(SQLModel, table=True):
    post_id: str = Field(default="", foreign_key="post.id", primary_key=True)
    tag_id: str = Field(default="", foreign_key="tag.id", primary_key=True)

class TagCategoryLink(SQLModel, table=True):
    tag_id: str = Field(default="", foreign_key="tag.id", primary_key=True)
    category_id: str = Field(default="", foreign_key="category.id", primary_key=True)

class Post(SQLModel, table=True):
    id: str = Field(default = "", primary_key=True)
    ext_id: str = Field(default="")
    name: str = Field(default="")
    artist_name: str = Field(default="")
    board: BOARD | None = Field(default=None)
    score: int = Field(default=0)
    url: str = Field(default="")
    website: str = Field(default="")
    board_update_str: str  = Field(default="")
    height: int = Field(default=0)
    width: int = Field(default=0)
    ratio: float = Field(default=0.0)
    ext: str = Field(default="")
    file_link: str = Field(default="")
    thumbnail_link: str = Field(default="")
    preview_link: str = Field(default="")
    tags: list["Tag"] = Relationship(back_populates="posts", link_model=PostTagLink)

class Tag(SQLModel, table=True):
    id: str = Field(default="", primary_key=True)
    posts: list[Post] | None = Relationship(back_populates="tags", link_model=PostTagLink)
    categories: list["Category"] | None = Relationship(back_populates="tags", link_model=TagCategoryLink)

class Category(SQLModel, table=True):
    id: str = Field(default="", primary_key=True)
    tags: list[Tag] = Relationship(back_populates="categories", link_model=TagCategoryLink)

class PostFile(SQLModel, table=True):
    post_id: str | None = Field(default=None, foreign_key="post.id", primary_key=True)
    height: int = Field(default=0)
    width: int = Field(default=0)
    ratio: float = Field(default=0.0)
    ext: str = Field(default="")

    file: str = Field(default="")
    thumbnail: str | None = Field(default=None)
    preview: str | None = Field(default=None)



if __name__ == "__main__":
    main()