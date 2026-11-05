import os
import oracledb
import logging

from config import uname, pwd, dsn, cdir, wltloc, wltpwd
from config import schema

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        self.uname = uname
        self.pwd = pwd
        self.dsn = dsn
        self.cdir = cdir
        self.wltloc = wltloc
        self.wltpwd = wltpwd
        self.pool = None

    def get_connection(self):
        if not self.pool:
            logger.info("Initializing Oracle Database connection pool")
            pool_kwargs = {
                "user": self.uname,
                "password": self.pwd,
                "dsn": self.dsn,
                "min": 2,
                "max": 10,
                "increment": 1
            }
            if self.cdir and os.path.isdir(self.cdir):
                pool_kwargs["config_dir"] = self.cdir
            if self.wltloc and os.path.isdir(self.wltloc):
                pool_kwargs["wallet_location"] = self.wltloc
                if self.wltpwd:
                    pool_kwargs["wallet_password"] = self.wltpwd

            self.pool = oracledb.create_pool(**pool_kwargs)
        return self.pool.acquire()


    def get_job_details(self, job_id: str) -> dict:
        logger.info(f"Getting job details for job ID: {job_id}")
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT JOB_DESCRIPTION FROM {schema}.JOBS_JOB_DETAILS WHERE ID = :job_id", {"job_id": job_id})
            job_details = cursor.fetchone()
            if job_details:
                return {"is_data_found": True, "data": str(job_details)}
            return {"is_data_found": False, "data": f"No job found with ID: {job_id}"}
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return {"is_data_found": False, "data": f"Error retrieving job details: {str(e)}"}
        finally:
            conn.close()

    def get_candidate_details(self, candidate_id: str) -> dict:
        logger.info(f"Getting candidate details for candidate ID: {candidate_id}")
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT PARAGRAPH_TEXT FROM {schema}.DOCUMENT_PARAGRAPHS WHERE DOCUMENT_ID = :candidate_id", {"candidate_id": candidate_id})
            for row in cursor:
                paragraph_text = row[0]
                if isinstance(paragraph_text, oracledb.LOB):
                    return {"is_data_found": True, "data": paragraph_text.read()}
                return {"is_data_found": True, "data": str(paragraph_text)}
            return {"is_data_found": False, "data": f"No candidate found with ID: {candidate_id}"}
        except Exception as e:
            logger.error(f"Error getting candidate details: {e}")
            return {"is_data_found": False, "data": f"Error retrieving candidate details: {str(e)}"}
        finally:
            conn.close()

    def run_query(self, query: str, params: dict = None) -> dict:
        logger.info(f"Running query: {query}")
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if schema:
                try:
                    cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
                except Exception as se:
                    logger.warning(f"Could not set schema: {se}")
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                formatted_rows = []
                for row in rows:
                    formatted_row = []
                    for item in row:
                        if isinstance(item, oracledb.LOB):
                            formatted_row.append(item.read())
                        else:
                            formatted_row.append(item)
                    formatted_rows.append(dict(zip(columns, formatted_row)))
                return {"is_data_found": True, "columns": columns, "data": formatted_rows}
            else:
                conn.commit()
                return {"is_data_found": True, "data": "Statement executed successfully"}
        except Exception as e:
            logger.error(f"Error running query: {e}")
            return {"is_data_found": False, "data": f"Error running query: {str(e)}"}
        finally:
            conn.close()

db_manager = DBManager()
