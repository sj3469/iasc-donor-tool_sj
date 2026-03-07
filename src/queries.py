"""
queries.py — Data query functions for the IASC Donor Analytics tool.
Uses the actual imported SQLite table built from mock_dataset3.csv.
"""

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "donors.db"

COL_CONTACT_ID = '"Contact ID"'
COL_ZIP = '"Mailing Zip/Postal Code"'
COL_FIRST_GIFT = '"First Gift Date"'
COL_LAST_GIFT = '"Last Gift Date"'
COL_AVG_GIFT = '"Average Gift"'
COL_TOTAL_GIFTS = '"Total Gifts"'
COL_NUM_GIFTS = '"Total Number of Gifts"'
COL_DONOR_STATUS = '"donor_status"'
COL_CREATED = '"contact_created_date"'
COL_SUB_TYPE = '"subscription_type"'
COL_SUB_STATUS = '"subscription_status"'
COL_EMAIL_OPEN = '"email_open_rate"'
COL_LAST_CLICK = '"last_email_click_date"'
COL_EVENT_COUNT = '"event_attendance_count"'
COL_GIVING_VEHICLE = '"giving_vehicle"'
COL_WEALTH = '"wealth_score"'


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _get_table_name() -> str:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY CASE WHEN name = 'contacts' THEN 0 ELSE 1 END, name
            """
        ).fetchall()

    if not rows:
        raise RuntimeError("No user tables found in donors.db")

    return rows[0]["name"]


def _select_donor_fields() -> str:
    return f"""
        {COL_CONTACT_ID} AS contact_id,
        {COL_ZIP} AS zip_code,
        {COL_FIRST_GIFT} AS first_gift_date,
        {COL_LAST_GIFT} AS last_gift_date,
        {COL_AVG_GIFT} AS average_gift,
        {COL_TOTAL_GIFTS} AS total_gifts,
        {COL_NUM_GIFTS} AS total_number_of_gifts,
        {COL_DONOR_STATUS} AS donor_status,
        {COL_CREATED} AS contact_created_date,
        {COL_SUB_TYPE} AS subscription_type,
        {COL_SUB_STATUS} AS subscription_status,
        {COL_EMAIL_OPEN} AS email_open_rate,
        {COL_LAST_CLICK} AS last_email_click_date,
        {COL_EVENT_COUNT} AS event_attendance_count,
        {COL_GIVING_VEHICLE} AS giving_vehicle,
        {COL_WEALTH} AS wealth_score
    """


def search_donors(
    state: Optional[str] = None,
    city: Optional[str] = None,
    donor_status: Optional[str] = None,
    sort_by: str = "total_gifts",
    sort_order: str = "desc",
    limit: int = 20,
    zip_code: Optional[str] = None,
) -> dict:
    table = _get_table_name()

    if state:
        return {
            "results": [],
            "count": 0,
            "summary": "This dataset does not include a state field. Try filtering by ZIP/postal code instead.",
        }

    if city:
        return {
            "results": [],
            "count": 0,
            "summary": "This dataset does not include a city field. Try filtering by ZIP/postal code instead.",
        }

    sort_map = {
        "total_gifts": COL_TOTAL_GIFTS,
        "average_gift": COL_AVG_GIFT,
        "wealth_score": COL_WEALTH,
        "last_gift_date": COL_LAST_GIFT,
        "contact_created_date": COL_CREATED,
    }
    order_col = sort_map.get(sort_by, COL_TOTAL_GIFTS)
    order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"
    limit = max(1, min(int(limit), 50))

    conditions = []
    params = []

    if zip_code:
        conditions.append(f"{COL_ZIP} = ?")
        params.append(str(zip_code))

    if donor_status:
        conditions.append(f"{COL_DONOR_STATUS} = ?")
        params.append(donor_status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            {_select_donor_fields()}
        FROM "{table}"
        {where_clause}
        ORDER BY {order_col} {order_dir}
        LIMIT ?
    """
    params.append(limit)

    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = _rows_to_dicts(rows)
    return {
        "results": results,
        "count": len(results),
        "summary": f"Found {len(results)} donors.",
    }


def get_donor_detail(contact_id: str) -> dict:
    table = _get_table_name()
    with get_db_connection() as conn:
        row = conn.execute(
            f"""
            SELECT
                {_select_donor_fields()}
            FROM "{table}"
            WHERE {COL_CONTACT_ID} = ?
            """,
            (contact_id,),
        ).fetchone()

    if row is None:
        return {"results": [], "count": 0, "summary": "No donor found."}

    return {"results": [dict(row)], "count": 1, "summary": "Found donor detail."}


def get_summary_statistics(group_by: Optional[str] = None) -> dict:
    table = _get_table_name()

    group_map = {
        "donor_status": COL_DONOR_STATUS,
        "subscription_type": COL_SUB_TYPE,
        "subscription_status": COL_SUB_STATUS,
        "giving_vehicle": COL_GIVING_VEHICLE,
    }

    with get_db_connection() as conn:
        if group_by in group_map:
            group_col = group_map[group_by]
            rows = conn.execute(
                f"""
                SELECT
                    {group_col} AS group_value,
                    COUNT(*) AS donor_count,
                    COALESCE(SUM({COL_TOTAL_GIFTS}), 0) AS total_giving
                FROM "{table}"
                GROUP BY {group_col}
                ORDER BY donor_count DESC, total_giving DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS donor_count,
                    COALESCE(SUM({COL_TOTAL_GIFTS}), 0) AS total_giving,
                    COALESCE(AVG({COL_TOTAL_GIFTS}), 0) AS avg_total_giving,
                    COALESCE(AVG({COL_AVG_GIFT}), 0) AS avg_gift,
                    COALESCE(AVG({COL_WEALTH}), 0) AS avg_wealth_score
                FROM "{table}"
                """
            ).fetchall()

    results = _rows_to_dicts(rows)
    return {
        "results": results,
        "count": len(results),
        "summary": "Summary statistics generated.",
    }


def get_geographic_distribution(limit: int = 50) -> dict:
    table = _get_table_name()
    limit = max(1, min(int(limit), 100))

    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                {COL_ZIP} AS zip_code,
                COUNT(*) AS donor_count,
                COALESCE(SUM({COL_TOTAL_GIFTS}), 0) AS total_giving
            FROM "{table}"
            GROUP BY {COL_ZIP}
            ORDER BY donor_count DESC, total_giving DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results = _rows_to_dicts(rows)
    return {
        "results": results,
        "count": len(results),
        "summary": "ZIP/postal-code distribution generated.",
    }


def get_lapsed_donors(limit: int = 50) -> dict:
    table = _get_table_name()
    limit = max(1, min(int(limit), 100))

    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                {_select_donor_fields()}
            FROM "{table}"
            WHERE {COL_DONOR_STATUS} = 'lapsed'
            ORDER BY {COL_TOTAL_GIFTS} DESC, {COL_WEALTH} DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results = _rows_to_dicts(rows)
    return {
        "results": results,
        "count": len(results),
        "summary": f"Found {len(results)} lapsed donors.",
    }


def get_prospects_by_potential(limit: int = 50) -> dict:
    table = _get_table_name()
    limit = max(1, min(int(limit), 100))

    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                {_select_donor_fields()}
            FROM "{table}"
            WHERE {COL_DONOR_STATUS} = 'prospect'
            ORDER BY {COL_WEALTH} DESC, {COL_EMAIL_OPEN} DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results = _rows_to_dicts(rows)
    return {
        "results": results,
        "count": len(results),
        "summary": f"Found {len(results)} prospects.",
    }


def plan_fundraising_trip(target_state: str, limit: int = 20) -> dict:
    return {
        "results": [],
        "count": 0,
        "summary": "Trip-by-state is unavailable because this dataset has ZIP/postal code but no state field.",
    }

