import unittest
from src.schema_inspector import get_schema_representation


class TestSchemaInspector(unittest.TestCase):
    def test_schema_contains_albums_table(self):
        schema = get_schema_representation(db_path="chinook.db")
        self.assertIn("Table: albums", schema)
        self.assertIn("AlbumId (PK)", schema)
        self.assertIn("Title", schema)
        self.assertIn("ArtistId (FK -> artists.ArtistId)", schema)


if __name__ == "__main__":
    unittest.main()
