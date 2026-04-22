from django.db import migrations


def repair_show_payment_on_link_column(apps, schema_editor):
    """
    Repair local DBs that may have diverged while renaming the field:
    - If old column exists and new doesn't, rename old -> new.
    - If neither exists, add new with default true.
    - If new already exists, no-op.
    """
    connection = schema_editor.connection
    table_name = "jobs_job"
    old_col = "show_payment_on_driver_link"
    new_col = "show_payment_on_link"

    with connection.cursor() as cursor:
        columns = {
            row.name
            for row in connection.introspection.get_table_description(cursor, table_name)
        }

        if new_col in columns:
            return

        if old_col in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} RENAME COLUMN {old_col} TO {new_col}"
            )
            return

        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {new_col} bool NOT NULL DEFAULT 1"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0050_job_show_payment_on_driver_link"),
    ]

    operations = [
        migrations.RunPython(
            repair_show_payment_on_link_column,
            migrations.RunPython.noop,
        ),
    ]
