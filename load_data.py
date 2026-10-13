"""
load_data.py
Loads the official Neo4j Movies dataset safely using PARAMETERIZED Cypher queries.
- Zero string interpolation into Cypher: safe against apostrophes (e.g. "Jerry O'Connell").
- Uses idempotent MERGE operations: safe to rerun without creating duplicates.
- Does NOT delete existing database data.
- Compatible with official Neo4j Python Driver and .env configuration.
"""

import sys
from typing import List, Dict, Any
from neo4j_connection import Neo4jConnection, get_neo4j_connection

# ==============================================================================
# STRUCTURED DATASET DEFINITION (Clean Python data types)
# ==============================================================================

MOVIES_DATA: List[Dict[str, Any]] = [
    {"title": "The Matrix", "released": 1999, "tagline": "Welcome to the Real World"},
    {"title": "The Matrix Reloaded", "released": 2003, "tagline": "Free your mind"},
    {"title": "The Matrix Revolutions", "released": 2003, "tagline": "Everything that has a beginning has an end"},
    {"title": "The Devil's Advocate", "released": 1997, "tagline": "Evil has its winning ways"},
    {"title": "A Few Good Men", "released": 1992, "tagline": "You can't handle the truth!"},
    {"title": "Top Gun", "released": 1986, "tagline": "I feel the need, the need for speed."},
    {"title": "Jerry Maguire", "released": 2000, "tagline": "The rest of his life begins now."},
    {"title": "Stand By Me", "released": 1986, "tagline": "For some, it's the last real adventure of a scout's life."},
    {"title": "Apollo 13", "released": 1995, "tagline": "Houston, we have a problem."},
    {"title": "Cast Away", "released": 2000, "tagline": "At the edge of the world, his journey begins."},
    {"title": "You've Got Mail", "released": 1998, "tagline": "At snacks. At work. At home."},
    {"title": "Sleepless in Seattle", "released": 1993, "tagline": "What if someone you never met, someone you never saw, someone you never knew was the only someone for you?"},
    {"title": "Joe Versus the Volcano", "released": 1990, "tagline": "A story of love, lava and true courage."},
    {"title": "When Harry Met Sally", "released": 1989, "tagline": "Can two friends sleep together and still remain friends?"},
    {"title": "Cloud Atlas", "released": 2012, "tagline": "Everything is connected"},
    {"title": "The Da Vinci Code", "released": 2006, "tagline": "Break the codes"},
    {"title": "A League of Their Own", "released": 1992, "tagline": "Once in a lifetime you get a chance to do something great"}
]

PEOPLE_DATA: List[Dict[str, Any]] = [
    # The Matrix Series
    {"name": "Keanu Reeves", "born": 1964},
    {"name": "Carrie-Anne Moss", "born": 1967},
    {"name": "Laurence Fishburne", "born": 1961},
    {"name": "Hugo Weaving", "born": 1960},
    {"name": "Lilly Wachowski", "born": 1967},
    {"name": "Lana Wachowski", "born": 1965},
    {"name": "Joel Silver", "born": 1952},

    # The Devil's Advocate
    {"name": "Charlize Theron", "born": 1975},
    {"name": "Al Pacino", "born": 1940},
    {"name": "Taylor Hackford", "born": 1944},

    # A Few Good Men
    {"name": "Tom Cruise", "born": 1962},
    {"name": "Jack Nicholson", "born": 1937},
    {"name": "Demi Moore", "born": 1962},
    {"name": "Kevin Bacon", "born": 1958},
    {"name": "Kiefer Sutherland", "born": 1966},
    {"name": "Noah Wyle", "born": 1971},
    {"name": "Cuba Gooding Jr.", "born": 1968},
    {"name": "Kevin Pollak", "born": 1957},
    {"name": "J.T. Walsh", "born": 1943},
    {"name": "James Marshall", "born": 1967},
    {"name": "Christopher Guest", "born": 1948},
    {"name": "Rob Reiner", "born": 1947},
    {"name": "Aaron Sorkin", "born": 1961},

    # Top Gun
    {"name": "Kelly McGillis", "born": 1957},
    {"name": "Val Kilmer", "born": 1959},
    {"name": "Anthony Edwards", "born": 1962},
    {"name": "Tom Skerritt", "born": 1933},
    {"name": "Meg Ryan", "born": 1961},
    {"name": "Tony Scott", "born": 1944},
    {"name": "Jim Cash", "born": 1941},

    # Jerry Maguire
    {"name": "Renee Zellweger", "born": 1969},
    {"name": "Kelly Preston", "born": 1962},
    {"name": "Jerry O'Connell", "born": 1974},
    {"name": "Jay Mohr", "born": 1970},
    {"name": "Bonnie Hunt", "born": 1961},
    {"name": "Regina King", "born": 1965},
    {"name": "Jonathan Lipnicki", "born": 1990},
    {"name": "Cameron Crowe", "born": 1957},

    # Stand By Me
    {"name": "River Phoenix", "born": 1970},
    {"name": "Corey Feldman", "born": 1971},
    {"name": "Wil Wheaton", "born": 1972},
    {"name": "John Cusack", "born": 1966},
    {"name": "Marshall Bell", "born": 1942},

    # Apollo 13
    {"name": "Tom Hanks", "born": 1956},
    {"name": "Ed Harris", "born": 1950},
    {"name": "Bill Paxton", "born": 1955},
    {"name": "Ron Howard", "born": 1954},
    {"name": "Gary Sinise", "born": 1955},

    # Cast Away
    {"name": "Helen Hunt", "born": 1963},
    {"name": "Robert Zemeckis", "born": 1951},

    # You've Got Mail
    {"name": "Parker Posey", "born": 1968},
    {"name": "Dave Chappelle", "born": 1973},
    {"name": "Steve Zahn", "born": 1967},
    {"name": "Greg Kinnear", "born": 1963},
    {"name": "Nora Ephron", "born": 1941},

    # Sleepless in Seattle
    {"name": "Bill Pullman", "born": 1953},
    {"name": "Victor Garber", "born": 1949},
    {"name": "Rita Wilson", "born": 1956},
    {"name": "Rosie O'Donnell", "born": 1962},

    # Joe Versus the Volcano
    {"name": "John Patrick Shanley", "born": 1950},

    # When Harry Met Sally
    {"name": "Billy Crystal", "born": 1948},
    {"name": "Carrie Fisher", "born": 1956},
    {"name": "Bruno Kirby", "born": 1949},

    # Cloud Atlas
    {"name": "Halle Berry", "born": 1966},
    {"name": "Jim Broadbent", "born": 1949},
    {"name": "Tom Tykwer", "born": 1965},

    # The Da Vinci Code
    {"name": "Audrey Tautou", "born": 1976},
    {"name": "Ian McKellen", "born": 1939},

    # A League of Their Own
    {"name": "Geena Davis", "born": 1956},
    {"name": "Madonna", "born": 1958},
    {"name": "Penny Marshall", "born": 1943}
]

ACTED_IN_DATA: List[Dict[str, Any]] = [
    # The Matrix
    {"person": "Keanu Reeves", "movie": "The Matrix", "roles": ["Neo"]},
    {"person": "Carrie-Anne Moss", "movie": "The Matrix", "roles": ["Trinity"]},
    {"person": "Laurence Fishburne", "movie": "The Matrix", "roles": ["Morpheus"]},
    {"person": "Hugo Weaving", "movie": "The Matrix", "roles": ["Agent Smith"]},

    # The Matrix Reloaded
    {"person": "Keanu Reeves", "movie": "The Matrix Reloaded", "roles": ["Neo"]},
    {"person": "Carrie-Anne Moss", "movie": "The Matrix Reloaded", "roles": ["Trinity"]},
    {"person": "Laurence Fishburne", "movie": "The Matrix Reloaded", "roles": ["Morpheus"]},
    {"person": "Hugo Weaving", "movie": "The Matrix Reloaded", "roles": ["Agent Smith"]},

    # The Matrix Revolutions
    {"person": "Keanu Reeves", "movie": "The Matrix Revolutions", "roles": ["Neo"]},
    {"person": "Carrie-Anne Moss", "movie": "The Matrix Revolutions", "roles": ["Trinity"]},
    {"person": "Laurence Fishburne", "movie": "The Matrix Revolutions", "roles": ["Morpheus"]},
    {"person": "Hugo Weaving", "movie": "The Matrix Revolutions", "roles": ["Agent Smith"]},

    # The Devil's Advocate
    {"person": "Keanu Reeves", "movie": "The Devil's Advocate", "roles": ["Kevin Lomax"]},
    {"person": "Charlize Theron", "movie": "The Devil's Advocate", "roles": ["Mary Ann Lomax"]},
    {"person": "Al Pacino", "movie": "The Devil's Advocate", "roles": ["John Milton"]},

    # A Few Good Men
    {"person": "Tom Cruise", "movie": "A Few Good Men", "roles": ["Lt. Daniel Kaffee"]},
    {"person": "Jack Nicholson", "movie": "A Few Good Men", "roles": ["Col. Nathan R. Jessep"]},
    {"person": "Demi Moore", "movie": "A Few Good Men", "roles": ["Lt. Cdr. JoAnne Galloway"]},
    {"person": "Kevin Bacon", "movie": "A Few Good Men", "roles": ["Capt. Jack Challee"]},
    {"person": "Kiefer Sutherland", "movie": "A Few Good Men", "roles": ["Lt. Jonathan Kendrick"]},
    {"person": "Noah Wyle", "movie": "A Few Good Men", "roles": ["Cpl. Jeffrey Barnes"]},
    {"person": "Cuba Gooding Jr.", "movie": "A Few Good Men", "roles": ["Cpl. Carl Hammaker"]},
    {"person": "Kevin Pollak", "movie": "A Few Good Men", "roles": ["Lt. Sam Weinberg"]},
    {"person": "J.T. Walsh", "movie": "A Few Good Men", "roles": ["Lt. Col. Matthew Andrew Markinson"]},
    {"person": "James Marshall", "movie": "A Few Good Men", "roles": ["Pfc. Louden Downey"]},
    {"person": "Christopher Guest", "movie": "A Few Good Men", "roles": ["Dr. Stone"]},
    {"person": "Aaron Sorkin", "movie": "A Few Good Men", "roles": ["Man in Bar"]},

    # Top Gun
    {"person": "Tom Cruise", "movie": "Top Gun", "roles": ["Maverick"]},
    {"person": "Kelly McGillis", "movie": "Top Gun", "roles": ["Charlie"]},
    {"person": "Val Kilmer", "movie": "Top Gun", "roles": ["Iceman"]},
    {"person": "Anthony Edwards", "movie": "Top Gun", "roles": ["Goose"]},
    {"person": "Tom Skerritt", "movie": "Top Gun", "roles": ["Viper"]},
    {"person": "Meg Ryan", "movie": "Top Gun", "roles": ["Carole"]},

    # Jerry Maguire
    {"person": "Tom Cruise", "movie": "Jerry Maguire", "roles": ["Jerry Maguire"]},
    {"person": "Cuba Gooding Jr.", "movie": "Jerry Maguire", "roles": ["Rod Tidwell"]},
    {"person": "Renee Zellweger", "movie": "Jerry Maguire", "roles": ["Dorothy Boyd"]},
    {"person": "Kelly Preston", "movie": "Jerry Maguire", "roles": ["Avery Bishop"]},
    {"person": "Jerry O'Connell", "movie": "Jerry Maguire", "roles": ["Frank Cushman"]},
    {"person": "Jay Mohr", "movie": "Jerry Maguire", "roles": ["Bob Sugar"]},
    {"person": "Bonnie Hunt", "movie": "Jerry Maguire", "roles": ["Laurel Boyd"]},
    {"person": "Regina King", "movie": "Jerry Maguire", "roles": ["Marcee Tidwell"]},
    {"person": "Jonathan Lipnicki", "movie": "Jerry Maguire", "roles": ["Ray Boyd"]},

    # Stand By Me
    {"person": "Wil Wheaton", "movie": "Stand By Me", "roles": ["Gordie Lachance"]},
    {"person": "River Phoenix", "movie": "Stand By Me", "roles": ["Chris Chambers"]},
    {"person": "Jerry O'Connell", "movie": "Stand By Me", "roles": ["Vern Tessio"]},
    {"person": "Corey Feldman", "movie": "Stand By Me", "roles": ["Teddy Duchamp"]},
    {"person": "John Cusack", "movie": "Stand By Me", "roles": ["Denny Lachance"]},
    {"person": "Kiefer Sutherland", "movie": "Stand By Me", "roles": ["Ace Walsh"]},
    {"person": "Marshall Bell", "movie": "Stand By Me", "roles": ["Mr. Lachance"]},

    # Apollo 13
    {"person": "Tom Hanks", "movie": "Apollo 13", "roles": ["Jim Lovell"]},
    {"person": "Kevin Bacon", "movie": "Apollo 13", "roles": ["Jack Swigert"]},
    {"person": "Ed Harris", "movie": "Apollo 13", "roles": ["Gene Kranz"]},
    {"person": "Bill Paxton", "movie": "Apollo 13", "roles": ["Fred Haise"]},
    {"person": "Gary Sinise", "movie": "Apollo 13", "roles": ["Ken Mattingly"]},

    # Cast Away
    {"person": "Tom Hanks", "movie": "Cast Away", "roles": ["Chuck Noland"]},
    {"person": "Helen Hunt", "movie": "Cast Away", "roles": ["Kelly Frears"]},

    # You've Got Mail
    {"person": "Tom Hanks", "movie": "You've Got Mail", "roles": ["Joe Fox"]},
    {"person": "Meg Ryan", "movie": "You've Got Mail", "roles": ["Kathleen Kelly"]},
    {"person": "Greg Kinnear", "movie": "You've Got Mail", "roles": ["Frank Navasky"]},
    {"person": "Parker Posey", "movie": "You've Got Mail", "roles": ["Patricia Eden"]},
    {"person": "Dave Chappelle", "movie": "You've Got Mail", "roles": ["Kevin Jackson"]},
    {"person": "Steve Zahn", "movie": "You've Got Mail", "roles": ["George Pappas"]},

    # Sleepless in Seattle
    {"person": "Tom Hanks", "movie": "Sleepless in Seattle", "roles": ["Sam Baldwin"]},
    {"person": "Meg Ryan", "movie": "Sleepless in Seattle", "roles": ["Annie Reed"]},
    {"person": "Bill Pullman", "movie": "Sleepless in Seattle", "roles": ["Walter"]},
    {"person": "Victor Garber", "movie": "Sleepless in Seattle", "roles": ["Greg"]},
    {"person": "Rita Wilson", "movie": "Sleepless in Seattle", "roles": ["Suzy"]},
    {"person": "Rosie O'Donnell", "movie": "Sleepless in Seattle", "roles": ["Becky"]},

    # Joe Versus the Volcano
    {"person": "Tom Hanks", "movie": "Joe Versus the Volcano", "roles": ["Joe Banks"]},
    {"person": "Meg Ryan", "movie": "Joe Versus the Volcano", "roles": ["DeDe", "Angelica Graynamore", "Patricia Graynamore"]},

    # When Harry Met Sally
    {"person": "Billy Crystal", "movie": "When Harry Met Sally", "roles": ["Harry Burns"]},
    {"person": "Meg Ryan", "movie": "When Harry Met Sally", "roles": ["Sally Albright"]},
    {"person": "Carrie Fisher", "movie": "When Harry Met Sally", "roles": ["Marie"]},
    {"person": "Bruno Kirby", "movie": "When Harry Met Sally", "roles": ["Jess"]},

    # Cloud Atlas
    {"person": "Tom Hanks", "movie": "Cloud Atlas", "roles": ["Dermot Hoggins", "Isaac Sachs", "Dr. Henry Goose", "Zachry"]},
    {"person": "Halle Berry", "movie": "Cloud Atlas", "roles": ["Luisa Rey", "Jocasta Ayrs", "Meronym"]},
    {"person": "Jim Broadbent", "movie": "Cloud Atlas", "roles": ["Vyvyan Ayrs", "Timothy Cavendish"]},
    {"person": "Hugo Weaving", "movie": "Cloud Atlas", "roles": ["Bill Smoke", "Haskell Moore", "Nurse Noakes"]},

    # The Da Vinci Code
    {"person": "Tom Hanks", "movie": "The Da Vinci Code", "roles": ["Dr. Robert Langdon"]},
    {"person": "Audrey Tautou", "movie": "The Da Vinci Code", "roles": ["Sophie Neveu"]},
    {"person": "Ian McKellen", "movie": "The Da Vinci Code", "roles": ["Sir Leigh Teabing"]},

    # A League of Their Own
    {"person": "Tom Hanks", "movie": "A League of Their Own", "roles": ["Jimmy Dugan"]},
    {"person": "Geena Davis", "movie": "A League of Their Own", "roles": ["Dottie Hinson"]},
    {"person": "Madonna", "movie": "A League of Their Own", "roles": ["Mae Mordabito"]},
    {"person": "Rosie O'Donnell", "movie": "A League of Their Own", "roles": ["Doris Murphy"]},
    {"person": "Bill Pullman", "movie": "A League of Their Own", "roles": ["Bob Hinson"]}
]

DIRECTED_DATA: List[Dict[str, str]] = [
    {"person": "Lilly Wachowski", "movie": "The Matrix"},
    {"person": "Lana Wachowski", "movie": "The Matrix"},
    {"person": "Lilly Wachowski", "movie": "The Matrix Reloaded"},
    {"person": "Lana Wachowski", "movie": "The Matrix Reloaded"},
    {"person": "Lilly Wachowski", "movie": "The Matrix Revolutions"},
    {"person": "Lana Wachowski", "movie": "The Matrix Revolutions"},
    {"person": "Taylor Hackford", "movie": "The Devil's Advocate"},
    {"person": "Rob Reiner", "movie": "A Few Good Men"},
    {"person": "Tony Scott", "movie": "Top Gun"},
    {"person": "Cameron Crowe", "movie": "Jerry Maguire"},
    {"person": "Rob Reiner", "movie": "Stand By Me"},
    {"person": "Ron Howard", "movie": "Apollo 13"},
    {"person": "Robert Zemeckis", "movie": "Cast Away"},
    {"person": "Nora Ephron", "movie": "You've Got Mail"},
    {"person": "Nora Ephron", "movie": "Sleepless in Seattle"},
    {"person": "John Patrick Shanley", "movie": "Joe Versus the Volcano"},
    {"person": "Rob Reiner", "movie": "When Harry Met Sally"},
    {"person": "Lana Wachowski", "movie": "Cloud Atlas"},
    {"person": "Lilly Wachowski", "movie": "Cloud Atlas"},
    {"person": "Tom Tykwer", "movie": "Cloud Atlas"},
    {"person": "Ron Howard", "movie": "The Da Vinci Code"},
    {"person": "Penny Marshall", "movie": "A League of Their Own"}
]

PRODUCED_DATA: List[Dict[str, str]] = [
    {"person": "Joel Silver", "movie": "The Matrix"},
    {"person": "Joel Silver", "movie": "The Matrix Reloaded"},
    {"person": "Joel Silver", "movie": "The Matrix Revolutions"},
    {"person": "Cameron Crowe", "movie": "Jerry Maguire"}
]

WROTE_DATA: List[Dict[str, str]] = [
    {"person": "Aaron Sorkin", "movie": "A Few Good Men"},
    {"person": "Jim Cash", "movie": "Top Gun"},
    {"person": "Cameron Crowe", "movie": "Jerry Maguire"},
    {"person": "Nora Ephron", "movie": "You've Got Mail"},
    {"person": "Nora Ephron", "movie": "Sleepless in Seattle"},
    {"person": "John Patrick Shanley", "movie": "Joe Versus the Volcano"},
    {"person": "Nora Ephron", "movie": "When Harry Met Sally"}
]


# ==============================================================================
# PARAMETERIZED CYPHER LOADER FUNCTIONS
# ==============================================================================

def load_movies(conn: Neo4jConnection, movies: List[Dict[str, Any]]) -> int:
    """Merges movie nodes using parameterized Cypher."""
    cypher = """
    UNWIND $batch AS item
    MERGE (m:Movie {title: item.title})
    SET m.released = item.released,
        m.tagline = item.tagline
    RETURN count(m) AS total
    """
    res = conn.execute_write_query(cypher, {"batch": movies})
    return res[0]["total"] if res else len(movies)


def load_people(conn: Neo4jConnection, people: List[Dict[str, Any]]) -> int:
    """Merges person nodes using parameterized Cypher."""
    cypher = """
    UNWIND $batch AS item
    MERGE (p:Person {name: item.name})
    SET p.born = item.born
    RETURN count(p) AS total
    """
    res = conn.execute_write_query(cypher, {"batch": people})
    return res[0]["total"] if res else len(people)


def load_acted_in(conn: Neo4jConnection, acted_in: List[Dict[str, Any]]) -> int:
    """Merges ACTED_IN relationships using parameterized Cypher."""
    cypher = """
    UNWIND $batch AS item
    MATCH (p:Person {name: item.person})
    MATCH (m:Movie {title: item.movie})
    MERGE (p)-[r:ACTED_IN]->(m)
    SET r.roles = item.roles
    RETURN count(r) AS total
    """
    res = conn.execute_write_query(cypher, {"batch": acted_in})
    return res[0]["total"] if res else len(acted_in)


def load_directed(conn: Neo4jConnection, directed: List[Dict[str, str]]) -> int:
    """Merges DIRECTED relationships using parameterized Cypher."""
    cypher = """
    UNWIND $batch AS item
    MATCH (p:Person {name: item.person})
    MATCH (m:Movie {title: item.movie})
    MERGE (p)-[r:DIRECTED]->(m)
    RETURN count(r) AS total
    """
    res = conn.execute_write_query(cypher, {"batch": directed})
    return res[0]["total"] if res else len(directed)


def load_produced(conn: Neo4jConnection, produced: List[Dict[str, str]]) -> int:
    """Merges PRODUCED relationships using parameterized Cypher."""
    cypher = """
    UNWIND $batch AS item
    MATCH (p:Person {name: item.person})
    MATCH (m:Movie {title: item.movie})
    MERGE (p)-[r:PRODUCED]->(m)
    RETURN count(r) AS total
    """
    res = conn.execute_write_query(cypher, {"batch": produced})
    return res[0]["total"] if res else len(produced)


def load_wrote(conn: Neo4jConnection, wrote: List[Dict[str, str]]) -> int:
    """Merges WROTE relationships using parameterized Cypher."""
    cypher = """
    UNWIND $batch AS item
    MATCH (p:Person {name: item.person})
    MATCH (m:Movie {title: item.movie})
    MERGE (p)-[r:WROTE]->(m)
    RETURN count(r) AS total
    """
    res = conn.execute_write_query(cypher, {"batch": wrote})
    return res[0]["total"] if res else len(wrote)


def verify_special_character_entities(conn: Neo4jConnection) -> None:
    """Verifies that entities with apostrophes or special characters loaded properly."""
    print("\n[VERIFICATION] Testing special-character entities via parameterized Cypher...")
    
    test_cases = [
        ("Jerry O'Connell", "MATCH (p:Person {name: $val}) RETURN p.name AS name, p.born AS born"),
        ("Rosie O'Donnell", "MATCH (p:Person {name: $val}) RETURN p.name AS name, p.born AS born"),
        ("The Devil's Advocate", "MATCH (m:Movie {title: $val}) RETURN m.title AS title, m.released AS released"),
        ("You've Got Mail", "MATCH (m:Movie {title: $val}) RETURN m.title AS title, m.released AS released")
    ]

    for val, query in test_cases:
        records = conn.execute_read_query(query, {"val": val})
        if records:
            print(f"  [OK] Found entity '{val}': {records[0]}")
        else:
            print(f"  [WARN] Entity '{val}' was not found in database.")


def load_dataset() -> bool:
    """
    Loads/merges the entire Neo4j Movies dataset safely into the database.
    Does not delete existing data, handles special characters, and is safe to rerun.
    """
    print("=" * 65)
    print("Neo4j Movies Dataset Loader (Parameterized & Idempotent)")
    print("=" * 65)

    conn = get_neo4j_connection()
    is_connected, msg = conn.verify_connectivity()
    if not is_connected:
        print(f"[ERROR] Could not connect to Neo4j: {msg}")
        print("Please verify NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in .env.")
        return False

    print(f"[INFO] Connection verified: {msg}")

    # Display initial counts (No database wipe or delete prompt)
    stats_before = conn.get_database_statistics()
    print(f"[INFO] Current database status:")
    print(f"       Movies: {stats_before.get('movie_count', 0)} | People: {stats_before.get('person_count', 0)}")
    print(f"       ACTED_IN: {stats_before.get('acted_in_count', 0)} | DIRECTED: {stats_before.get('directed_count', 0)}")
    print("[INFO] Starting idempotent MERGE operations (safe to rerun, no duplicates)...\n")

    try:
        # Step 1: Merge Movies
        print(f"[1/6] Merging {len(MOVIES_DATA)} Movie nodes...")
        load_movies(conn, MOVIES_DATA)
        print("      Done.")

        # Step 2: Merge People (Including Jerry O'Connell, Rosie O'Donnell, etc.)
        print(f"[2/6] Merging {len(PEOPLE_DATA)} Person nodes (including special characters)...")
        load_people(conn, PEOPLE_DATA)
        print("      Done.")

        # Step 3: Merge ACTED_IN
        print(f"[3/6] Merging {len(ACTED_IN_DATA)} ACTED_IN relationships...")
        load_acted_in(conn, ACTED_IN_DATA)
        print("      Done.")

        # Step 4: Merge DIRECTED
        print(f"[4/6] Merging {len(DIRECTED_DATA)} DIRECTED relationships...")
        load_directed(conn, DIRECTED_DATA)
        print("      Done.")

        # Step 5: Merge PRODUCED
        print(f"[5/6] Merging {len(PRODUCED_DATA)} PRODUCED relationships...")
        load_produced(conn, PRODUCED_DATA)
        print("      Done.")

        # Step 6: Merge WROTE
        print(f"[6/6] Merging {len(WROTE_DATA)} WROTE relationships...")
        load_wrote(conn, WROTE_DATA)
        print("      Done.")

        # Verification step for special character names
        verify_special_character_entities(conn)

        # Final Summary
        stats_after = conn.get_database_statistics()
        print("\n" + "=" * 65)
        print("[SUCCESS] Movie dataset merged into Neo4j successfully!")
        print(f"Total Movies in DB:       {stats_after.get('movie_count', 0)}")
        print(f"Total People in DB:       {stats_after.get('person_count', 0)}")
        print(f"Total ACTED_IN in DB:     {stats_after.get('acted_in_count', 0)}")
        print(f"Total DIRECTED in DB:     {stats_after.get('directed_count', 0)}")
        print("=" * 65)
        return True

    except Exception as e:
        print(f"\n[ERROR] Data insertion failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = load_dataset()
    sys.exit(0 if success else 1)
