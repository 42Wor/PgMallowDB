import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import config
import json
from datetime import datetime
import math
import pandas as pd
from io import StringIO
import csv

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Use the actual config if available
try:
    from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
except ImportError:
    # Fallback to environment variables or hardcoded values
    import os

    DB_NAME = os.environ.get('DB_NAME', 'your_database_name')
    DB_USER = os.environ.get('DB_USER', 'your_username')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_password')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        flash(f"Database connection failed: {e}", "error")
        return None
    except psycopg2.Error as e:
        flash(f"Database error: {e}", "error")
        return None


def get_all_user_tables(cursor):
    """Fetches a list of all non-system tables from the public schema."""
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    return [row[0] for row in cursor.fetchall()]


def get_table_structure(cursor, table_name):
    """Gets the column structure for a table."""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return cursor.fetchall()


def get_database_size(cursor):
    """Returns the size of the database."""
    cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    return cursor.fetchone()[0]


def get_table_sizes(cursor):
    """Returns sizes of all tables."""
    cursor.execute("""
        SELECT table_name, 
               pg_size_pretty(pg_relation_size(quote_ident(table_name))) as size
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY pg_relation_size(quote_ident(table_name)) DESC;
    """)
    return cursor.fetchall()


def get_active_connections(cursor):
    """Returns number of active connections."""
    cursor.execute("SELECT COUNT(*) FROM pg_stat_activity")
    return cursor.fetchone()[0]


@app.route('/')
def index():
    """Main page: Displays database overview and navigation."""
    conn = get_db_connection()
    if not conn:
        return render_template('index.html', stats=None, tables_data=None, connection_error=True)

    stats = {}
    tables_data = []

    try:
        with conn.cursor() as cursor:
            # Get database stats
            stats['size'] = get_database_size(cursor)
            stats['active_connections'] = get_active_connections(cursor)

            # Get table information
            tables = get_all_user_tables(cursor)
            stats['table_count'] = len(tables)

            total_rows = 0
            for table_name in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                row_count = cursor.fetchone()[0]
                total_rows += row_count

                # Get table size
                cursor.execute(f"SELECT pg_size_pretty(pg_relation_size('{table_name}'))")
                table_size = cursor.fetchone()[0]

                tables_data.append({
                    'name': table_name,
                    'row_count': row_count,
                    'size': table_size
                })

            stats['total_rows'] = total_rows

    except Exception as e:
        flash(f"Error retrieving database information: {e}", "error")
        return render_template('index.html', stats=None, tables_data=None, connection_error=True)
    finally:
        if conn:
            conn.close()

    return render_template('index.html', stats=stats, tables_data=tables_data, connection_error=False)


@app.route('/tables')
def view_tables():
    """Displays all tables in the database."""
    conn = get_db_connection()
    if not conn:
        return render_template('tables.html', tables=[], connection_error=True)

    try:
        with conn.cursor() as cursor:
            tables = get_all_user_tables(cursor)
            table_info = []

            for table_name in tables:
                # Get row count for each table
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                row_count = cursor.fetchone()[0]

                # Get column info
                structure = get_table_structure(cursor, table_name)

                # Get table size
                cursor.execute(f"SELECT pg_size_pretty(pg_relation_size('{table_name}'))")
                table_size = cursor.fetchone()[0]

                table_info.append({
                    'name': table_name,
                    'row_count': row_count,
                    'size': table_size,
                    'columns': structure
                })

        return render_template('tables.html', tables=table_info, connection_error=False)

    except Exception as e:
        flash(f"Error retrieving tables: {e}", "error")
        return render_template('tables.html', tables=[], connection_error=True)
    finally:
        if conn:
            conn.close()


@app.route('/table/<table_name>')
def view_table_data(table_name):
    """Displays data from a specific table."""
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('view_tables'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page

    try:
        with conn.cursor() as cursor:
            # Get column names
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 1')
            columns = [desc[0] for desc in cursor.description]

            # Get total count for pagination
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            total_count = cursor.fetchone()[0]
            total_pages = math.ceil(total_count / per_page) if per_page > 0 else 1

            # Get data with pagination
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s', (per_page, offset))
            rows = cursor.fetchall()

            return render_template('table_data.html',
                                   table_name=table_name,
                                   columns=columns,
                                   rows=rows,
                                   page=page,
                                   per_page=per_page,
                                   total_count=total_count,
                                   total_pages=total_pages)

    except Exception as e:
        flash(f"Error retrieving data from {table_name}: {e}", "error")
        return redirect(url_for('view_tables'))
    finally:
        if conn:
            conn.close()


@app.route('/sql_editor', methods=['GET', 'POST'])
def sql_editor():
    """SQL Editor for executing custom queries."""
    if request.method == 'POST':
        query = request.form.get('query', '')
        if not query:
            flash("Please enter a SQL query", "warning")
            return render_template('sql_editor.html')

        conn = get_db_connection()
        if not conn:
            return render_template('sql_editor.html')

        try:
            with conn.cursor() as cursor:
                cursor.execute(query)

                if query.strip().lower().startswith('select'):
                    # For SELECT queries, show results
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    rowcount = len(rows)
                    message = f"Query returned {rowcount} row(s)"
                    return render_template('sql_editor.html',
                                           query=query,
                                           columns=columns,
                                           rows=rows,
                                           message=message)
                else:
                    # For other queries, show affected rows
                    conn.commit()
                    rowcount = cursor.rowcount
                    message = f"Query executed successfully. {rowcount} row(s) affected."
                    flash(message, "success")
                    return render_template('sql_editor.html', query=query, message=message)

        except Exception as e:
            error_msg = f"Error executing query: {e}"
            flash(error_msg, "error")
            return render_template('sql_editor.html', query=query, error=error_msg)
        finally:
            if conn:
                conn.close()

    return render_template('sql_editor.html')


@app.route('/api/execute_sql', methods=['POST'])
def execute_sql_api():
    """API endpoint for executing SQL queries (for AJAX requests)."""
    data = request.get_json()
    query = data.get('query', '')

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)

            if query.strip().lower().startswith('select'):
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()

                # Convert rows to list of dictionaries for JSON serialization
                result = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        # Handle non-serializable types like datetime
                        if isinstance(row[i], datetime):
                            row_dict[col] = row[i].isoformat()
                        else:
                            row_dict[col] = row[i]
                    result.append(row_dict)

                return jsonify({
                    'success': True,
                    'columns': columns,
                    'rows': result,
                    'rowcount': len(rows)
                })
            else:
                conn.commit()
                return jsonify({
                    'success': True,
                    'rowcount': cursor.rowcount,
                    'message': f'Query executed successfully. {cursor.rowcount} row(s) affected.'
                })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/export/<table_name>')
def export_table(table_name):
    """Exports table data as CSV."""
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('view_table_data', table_name=table_name))

    try:
        with conn.cursor() as cursor:
            cursor.execute(f'SELECT * FROM "{table_name}"')
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # Create CSV in memory
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            writer.writerows(rows)

            # Prepare response
            output.seek(0)
            return app.response_class(
                output,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename={table_name}.csv'}
            )

    except Exception as e:
        flash(f"Error exporting table {table_name}: {e}", "error")
        return redirect(url_for('view_table_data', table_name=table_name))
    finally:
        if conn:
            conn.close()


@app.route('/delete', methods=['GET', 'POST'])
def delete_data():
    """Shows the confirmation page and handles the actual deletion of all data."""
    if request.method == 'GET':
        return render_template('confirm_delete.html')

    # POST request - perform deletion
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index'))

    try:
        with conn.cursor() as cursor:
            tables = get_all_user_tables(cursor)
            for table_name in tables:
                # Use DELETE instead of TRUNCATE for more control
                query = '''DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;'''
                cursor.execute(query)
            conn.commit()
            flash("✅ Success! All data has been deleted from all tables.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error during deletion: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('index'))


@app.route('/table/<table_name>/delete', methods=['POST'])
def delete_table_data(table_name):
    """Deletes all data from a specific table."""
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('view_table_data', table_name=table_name))

    try:
        with conn.cursor() as cursor:
            cursor.execute(f'DELETE FROM "{table_name}"')
            conn.commit()
            flash(f"All data has been deleted from {table_name}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting data from {table_name}: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('view_table_data', table_name=table_name))


@app.route('/table/<table_name>/insert', methods=['GET', 'POST'])
def insert_data(table_name):
    """Allows inserting new data into a table."""
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('view_table_data', table_name=table_name))

    if request.method == 'GET':
        try:
            with conn.cursor() as cursor:
                # Get column information
                structure = get_table_structure(cursor, table_name)
                return render_template('insert_data.html', table_name=table_name, columns=structure)
        except Exception as e:
            flash(f"Error retrieving table structure: {e}", "error")
            return redirect(url_for('view_table_data', table_name=table_name))
        finally:
            if conn:
                conn.close()

    # POST request - insert data
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get form data
            columns = []
            values = []
            for key, value in request.form.items():
                if key != 'submit' and value:
                    columns.append(key)
                    values.append(value)

            if not columns:
                flash("No data provided for insertion.", "warning")
                return redirect(url_for('view_table_data', table_name=table_name))

            # Build INSERT query
            columns_str = ', '.join([f'"{col}"' for col in columns])
            placeholders = ', '.join(['%s'] * len(values))
            query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'

            cursor.execute(query, values)
            conn.commit()

            flash("Data inserted successfully.", "success")
            return redirect(url_for('view_table_data', table_name=table_name))

    except Exception as e:
        conn.rollback()
        flash(f"Error inserting data: {e}", "error")
        return redirect(url_for('view_table_data', table_name=table_name))
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
