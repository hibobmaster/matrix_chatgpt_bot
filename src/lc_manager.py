import sqlite3
import sys
from log import getlogger

logger = getlogger()


class LCManager:
    def __init__(self):
        try:
            self.conn = sqlite3.connect("manage_db")
            self.c = self.conn.cursor()
            self.c.execute(
                """
                CREATE TABLE IF NOT EXISTS lc_commands (
                    command_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    api_url TEXT NOT NULL,
                    api_key TEXT,
                    permission INTEGER NOT NULL
                )
                """
            )
            self.conn.commit()
        except Exception as e:
            logger.error(e, exc_info=True)
            sys.exit(1)

    def add_command(
        self,
        username: str,
        agent: str,
        api_url: str,
        api_key: str = None,
        permission: int = 0,
    ) -> None:
        # check if username and agent already exists
        self.c.execute(
            """
            SELECT username, agent FROM lc_commands
            WHERE username = ? AND agent = ?
            """,
            (username, agent),
        )
        if self.c.fetchone() is not None:
            raise Exception("agent already exists")

        self.c.execute(
            """
            INSERT INTO lc_commands (username, agent, api_url, api_key, permission)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, agent, api_url, api_key, permission),
        )
        self.conn.commit()

    def get_command_api_url(self, username: str, agent: str) -> list[any]:
        self.c.execute(
            """
            SELECT api_url FROM lc_commands
            WHERE username = ? AND agent = ?
            """,
            (username, agent),
        )
        return self.c.fetchall()

    def get_command_api_key(self, username: str, agent: str) -> list[any]:
        self.c.execute(
            """
            SELECT api_key FROM lc_commands
            WHERE username = ? AND agent = ?
            """,
            (username, agent),
        )
        return self.c.fetchall()

    def get_command_permission(self, username: str, agent: str) -> list[any]:
        self.c.execute(
            """
            SELECT permission FROM lc_commands
            WHERE username = ? AND agent = ?
            """,
            (username, agent),
        )
        return self.c.fetchall()

    def get_command_agent(self, username: str) -> list[any]:
        self.c.execute(
            """
            SELECT agent FROM lc_commands
            WHERE username = ?
            """,
            (username,),
        )
        return self.c.fetchall()

    def get_specific_by_username(self, username: str) -> list[any]:
        self.c.execute(
            """
            SELECT * FROM lc_commands
            WHERE username = ?
            """,
            (username,),
        )
        return self.c.fetchall()

    def get_specific_by_agent(self, agent: str) -> list[any]:
        self.c.execute(
            """
            SELECT * FROM lc_commands
            WHERE agent = ?
            """,
            (agent,),
        )
        return self.c.fetchall()

    def get_all(self) -> list[any]:
        self.c.execute(
            """
            SELECT * FROM lc_commands
            """
        )
        return self.c.fetchall()

    def update_command_api_url(self, username: str, agent: str, api_url: str) -> None:
        self.c.execute(
            """
            UPDATE lc_commands
            SET api_url = ?
            WHERE username = ? AND agent = ?
            """,
            (api_url, username, agent),
        )
        self.conn.commit()

    def update_command_api_key(self, username: str, agent: str, api_key: str) -> None:
        self.c.execute(
            """
            UPDATE lc_commands
            SET api_key = ?
            WHERE username = ? AND agent = ?
            """,
            (api_key, username, agent),
        )
        self.conn.commit()

    def update_command_permission(
        self, username: str, agent: str, permission: int
    ) -> None:
        self.c.execute(
            """
            UPDATE lc_commands
            SET permission = ?
            WHERE username = ? AND agent = ?
            """,
            (permission, username, agent),
        )
        self.conn.commit()

    def update_command_agent(self, username: str, agent: str, api_url: str) -> None:
        # check if agent already exists
        self.c.execute(
            """
            SELECT agent FROM lc_commands
            WHERE agent = ?
            """,
            (agent,),
        )
        if self.c.fetchone() is not None:
            raise Exception("agent already exists")
        self.c.execute(
            """
            UPDATE lc_commands
            SET agent = ?
            WHERE username = ? AND api_url = ?
            """,
            (agent, username, api_url),
        )
        self.conn.commit()

    def delete_command(self, username: str, agent: str) -> None:
        self.c.execute(
            """
            DELETE FROM lc_commands
            WHERE username = ? AND agent = ?
            """,
            (username, agent),
        )
        self.conn.commit()

    def delete_commands(self, username: str) -> None:
        self.c.execute(
            """
            DELETE FROM lc_commands
            WHERE username = ?
            """,
            (username,),
        )
        self.conn.commit()
