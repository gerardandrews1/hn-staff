# -*- coding: utf-8 -*-
"""
Utility: normalize Holiday Niseko API /bookings payload
into a flat DataFrame for Upcoming Arrivals.

Changes:
- arrival/departure are DATE-only (no time)
- guest_name is included; first/last retained in DF but not preferred for display
- eid is the first preferred column
- Updated to handle flat JSON structure with direct invoice/payment fields
"""
import pandas as pd
from pandas import json_normalize


def normalize_upcoming_arrivals(payload) -> pd.DataFrame:
    """
    Normalize /bookings payload to a flat, analysis-friendly DataFrame.

    Handles both nested (items) structure and flat structure.
    """
    # 1) Normalize shape to list[dict]
    if isinstance(payload, dict):
        payload = payload.get("bookings") or payload.get("data") or [payload]
    elif not isinstance(payload, list):
        payload = []

    if not payload:
        return pd.DataFrame()

    # 2) Handle the actual nested structure with lead_guest and items
    try:
        # Normalize with items as record path and lead_guest fields as meta
        meta_cols = [
            "eid", "id", "source", "segment", "extent", "active",
            "property_id", "property_name", "property_ja_id", "property_ja_name",
            ["lead_guest", "first_name"], 
            ["lead_guest", "last_name"],
            ["lead_guest", "email"], 
            ["lead_guest", "additional_email"], 
            ["lead_guest", "phone"],
        ]

        df_items = json_normalize(
            payload,
            record_path=["items"],
            meta=meta_cols,
            errors="ignore",
            max_level=1,
        )

        if not df_items.empty:
            # Rename columns to standard names
            df_items.rename(
                columns={
                    "check_in": "arrival_date",
                    "check_out": "departure_date",
                    "room_type_name": "room_type",
                    "lead_guest.first_name": "guest_first_name",
                    "lead_guest.last_name": "guest_last_name",
                    "lead_guest.email": "guest_email",
                    "lead_guest.additional_email": "guest_email_additional",
                    "lead_guest.phone": "guest_phone",
                },
                inplace=True,
            )

            # Parse dates and compute nights
            for c in ("arrival_date", "departure_date"):
                if c in df_items.columns:
                    df_items[c] = pd.to_datetime(df_items[c], errors="coerce").dt.date

            if {"arrival_date", "departure_date"} <= set(df_items.columns):
                a = pd.to_datetime(df_items["arrival_date"], errors="coerce")
                d = pd.to_datetime(df_items["departure_date"], errors="coerce")
                df_items["nights"] = (d - a).dt.days

            # Create guest_name
            if "guest_first_name" in df_items.columns or "guest_last_name" in df_items.columns:
                df_items["guest_name"] = (
                    df_items.get("guest_first_name", "").astype(str).fillna("")
                    + " "
                    + df_items.get("guest_last_name", "").astype(str).fillna("")
                ).str.strip()

            # Process invoices data - aggregate from invoices array
            try:
                inv_rows = []
                for rec in payload:
                    rec_id = rec.get("id")
                    invoices = rec.get("invoices", [])
                    
                    total_invoice_amount = 0
                    total_payment_amount = 0
                    
                    if invoices:  # If there are invoices
                        for inv in invoices:
                            inv_amount = inv.get("invoice_amount", 0) or 0
                            pay_amount = inv.get("payment_amount", 0) or 0
                            total_invoice_amount += inv_amount
                            total_payment_amount += pay_amount
                    
                    # Always add a row for each booking, even if no invoices
                    inv_rows.append({
                        "id": rec_id,
                        "invoices_total_amount": total_invoice_amount,
                        "payments_total_amount": total_payment_amount,
                        "invoices_count": len(invoices) if invoices else 0
                    })
                
                # Create invoice DataFrame and merge
                if inv_rows:
                    inv_df = pd.DataFrame(inv_rows)
                    df_items = df_items.merge(inv_df, on="id", how="left")
                else:
                    df_items["invoices_total_amount"] = 0
                    df_items["payments_total_amount"] = 0
                    df_items["invoices_count"] = 0
                
            except Exception as e:
                # If invoice processing fails, add empty columns
                df_items["invoices_total_amount"] = 0
                df_items["payments_total_amount"] = 0
                df_items["invoices_count"] = 0

            return df_items

    except Exception as e:
        # If the normalization fails, fall back to simple approach
        pass

    # 3) Original logic for nested structure with items
    meta_cols = [
        "eid", "id", "source", "segment", "extent", "active",
        "property_id", "property_name", "property_ja_id", "property_ja_name",
        ["lead_guest", "first_name"], ["lead_guest", "last_name"],
        ["lead_guest", "email"], ["lead_guest", "additional_email"], ["lead_guest", "phone"],
    ]

    df_items = json_normalize(
        payload,
        record_path=["items"],
        meta=meta_cols,
        errors="ignore",
        max_level=1,
    )

    if df_items.empty:
        # Fall back: no 'items' present — return flattened parents
        return json_normalize(payload, max_level=2)

    # 4) Friendly column names
    df_items.rename(
        columns={
            "check_in": "arrival_date",
            "check_out": "departure_date",
            "room_type_name": "room_type",
            "lead_guest.first_name": "guest_first_name",
            "lead_guest.last_name": "guest_last_name",
            "lead_guest.email": "guest_email",
            "lead_guest.additional_email": "guest_email_additional",
            "lead_guest.phone": "guest_phone",
        },
        inplace=True,
    )

    # 5) Parse dates (DATE only) & compute nights
    for c in ("arrival_date", "departure_date"):
        if c in df_items.columns:
            df_items[c] = pd.to_datetime(df_items[c], errors="coerce").dt.date

    if {"arrival_date", "departure_date"} <= set(df_items.columns):
        a = pd.to_datetime(df_items["arrival_date"], errors="coerce")
        d = pd.to_datetime(df_items["departure_date"], errors="coerce")
        df_items["nights"] = (d - a).dt.days

    # 6) guest_name (keep first/last columns in DF, but prefer guest_name for display)
    if "guest_first_name" in df_items.columns or "guest_last_name" in df_items.columns:
        df_items["guest_name"] = (
            df_items.get("guest_first_name", "").astype(str).fillna("")
            + " "
            + df_items.get("guest_last_name", "").astype(str).fillna("")
        ).str.strip()

    # 7) Invoices summary (optional)
    try:
        inv_rows = []
        for rec in payload:
            invs = rec.get("invoices") or []
            for inv in invs:
                inv_rows.append({
                    "id": rec.get("id"),
                    "invoice_id": inv.get("invoice_id"),
                    "invoice_number": inv.get("invoice_number"),
                    "invoice_date": inv.get("invoice_date"),
                    "invoice_due_date": inv.get("invoice_due_date"),
                    "invoice_amount": inv.get("invoice_amount"),
                    "payment_id": inv.get("payment_id"),
                    "payment_date": inv.get("payment_date"),
                    "payment_amount": inv.get("payment_amount"),
                })
        if inv_rows:
            inv_df = pd.DataFrame(inv_rows)
            for c in ("invoice_date", "invoice_due_date", "payment_date"):
                if c in inv_df.columns:
                    inv_df[c] = pd.to_datetime(inv_df[c], errors="coerce").dt.date
            inv_agg = inv_df.groupby("id", as_index=False).agg(
                invoices_count=("invoice_id", "count"),
                invoices_total_amount=("invoice_amount", "sum"),
                payments_total_amount=("payment_amount", "sum"),
                last_invoice_number=("invoice_number", "last"),
                last_invoice_date=("invoice_date", "max"),
                last_payment_date=("payment_date", "max"),
            )
            df_items = df_items.merge(inv_agg, on="id", how="left")
    except Exception:
        pass

    # 8) Preferred column order (eid first; guest_name preferred over split)
    preferred = [
        "eid",
        "arrival_date", "departure_date", "nights",
        "property_name", "room_type",
        "guest_name",
        "source", "extent", "active",
        "id",
        "invoices_count", "invoices_total_amount", "payments_total_amount",
        "last_invoice_number", "last_invoice_date", "last_payment_date",
    ]
    cols = [c for c in preferred if c in df_items.columns] + [c for c in df_items.columns if c not in preferred]
    return df_items[cols]