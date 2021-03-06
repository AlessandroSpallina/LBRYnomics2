import config
import numpy as np
import sqlite3
import time


def create_db():

    # Connect to database file
    conn = sqlite3.connect("db/lbrynomics.db")
    c = conn.cursor()

    # Set pragmas
    c.execute("""
    PRAGMA journal_mode = WAL;
    """)

    # Create table for measurements
    c.execute("""
    CREATE TABLE IF NOT EXISTS measurements
        (id INTEGER PRIMARY KEY,
         time REAL NOT NULL,
         num_channels INTEGER NOT NULL,
         num_streams INTEGER NOT NULL,
         lbc_deposits REAL,
         num_supports INTEGER,
         lbc_supports REAL,
         ytsync_new_pending INGEGER,
         ytsync_pending_update INTEGER,
         ytsync_pending_upgrade INTEGER,
         ytsync_failed INTEGER);
    """)

    # Create indices
    c.execute("""
    CREATE INDEX IF NOT EXISTS time ON measurements (time);
    """)
    conn.close()


    
def test_history():
    """
    See whether the history table is populated. If not, populate it.
    Not the fastest ever method but this shouldn't really be needed very
    much.
    """

    print("Generating approximate historical data.", flush=True)

    # Connect to database file
    conn = sqlite3.connect("db/lbrynomics.db")
    c = conn.cursor()

    # Count rows of history in table
    rows = c.execute("""SELECT COUNT(*) FROM measurements
                        WHERE lbc_deposits IS NULL;""").fetchone()[0]
    if rows > 0:
        # No need to do anything if history exists
        conn.close()
        print("Done.\n")
        return

    # Estimate history
    conn = sqlite3.connect(config.claims_db_file)
    c = conn.cursor()

    # Obtain creation times from claims.db
    ts_channels = []
    ts_streams  = []
    for row in c.execute("SELECT creation_timestamp, claim_type FROM claim;"):
        if row[1] == 2:
            ts_channels.append(row[0])
        elif row[1] == 1:
            ts_streams.append(row[0])
    conn.close()

    # Sort times
    ts_channels = np.sort(np.array(ts_channels))
    ts_streams = np.sort(np.array(ts_streams))

    # Make fake measurements
    start = min(min(ts_channels), min(ts_streams)) - 0.5
    now = time.time()
    num = int((now - start)/config.interval)
    counts = np.zeros((2, num))
    n = 0
    for t in ts_channels:
        k = int((t - start)/config.interval)
        if k < num:
            counts[0, k] += 1
        n += 1
        print("    Processed {n} claims.".format(n=n), end="\r", flush=True)

    for t in ts_streams:
        k = int((t - start)/config.interval)
        if k < num:
            counts[1, k] += 1
        n += 1
        print("    Processed {n} claims.".format(n=n), end="\r", flush=True)
    print("")

    counts = np.cumsum(counts, axis=1)

    conn = sqlite3.connect("db/lbrynomics.db")
    c = conn.cursor()

    for i in range(counts.shape[1]):
        t = start + i*config.interval
        c.execute("""INSERT INTO measurements (time, num_channels, num_streams)
                     VALUES (?, ?, ?);""", (t, counts[0, i], counts[1, i]))
        print("    Inserted {rows} rows into database."\
                    .format(rows=i+1), end="\r", flush=True)
    print("")

    c.execute("COMMIT;")
    conn.close()
    print("Done.\n")

