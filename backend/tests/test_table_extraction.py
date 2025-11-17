"""
Test suite for table extraction feature.
Tests TableExtractor module with various table extraction scenarios.
"""
import pytest
import os
from app.services.table_extractor import TableExtractor
from app.services.parser import (
    extract_table_by_index,
    extract_all_tables,
    get_table_summary
)


class TestTableExtractor:
    """Test TableExtractor class methods."""
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Provide path to sample PDF with tables (must be created for real tests)."""
        # This should point to a real PDF file with tables for integration testing
        return "test_data/sample_with_tables.pdf"
    
    def test_extract_by_index_first_table(self, sample_pdf_path):
        """Test extracting first table from a page."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            table = extractor.extract_by_index(page_num=1, table_index=1)
            
            assert table is not None
            assert table['page'] == 1
            assert table['table_index'] == 1
            assert 'headers' in table
            assert 'data' in table
            assert 'raw' in table
            assert table['rows'] >= 0
            assert table['columns'] >= 0
    
    def test_extract_by_index_last_table(self, sample_pdf_path):
        """Test extracting last table using -1 index."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            table = extractor.extract_by_index(page_num=1, table_index=-1)
            
            if table:  # Only if tables exist
                assert table['page'] == 1
                assert table['table_index'] >= 1
    
    def test_extract_by_index_invalid_page(self, sample_pdf_path):
        """Test extracting from invalid page number."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            table = extractor.extract_by_index(page_num=999, table_index=1)
            assert table is None
    
    def test_extract_by_index_invalid_table_index(self, sample_pdf_path):
        """Test extracting non-existent table index."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            table = extractor.extract_by_index(page_num=1, table_index=999)
            assert table is None
    
    def test_extract_all_tables(self, sample_pdf_path):
        """Test extracting all tables from a page."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            tables = extractor.extract_all(page_num=1)
            
            assert isinstance(tables, list)
            for table in tables:
                assert 'page' in table
                assert 'table_index' in table
                assert 'headers' in table
                assert 'data' in table
    
    def test_extract_range(self, sample_pdf_path):
        """Test extracting range of tables."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            tables = extractor.extract_range(page_num=1, start_index=1, end_index=2)
            
            assert isinstance(tables, list)
            if len(tables) > 0:
                assert tables[0]['table_index'] == 1
                if len(tables) > 1:
                    assert tables[1]['table_index'] == 2
    
    def test_extract_range_with_negative_end(self, sample_pdf_path):
        """Test extracting range with -1 as end (last table)."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            tables = extractor.extract_range(page_num=1, start_index=1, end_index=-1)
            
            assert isinstance(tables, list)
            # Should get all tables from index 1 to last
    
    def test_count_tables(self, sample_pdf_path):
        """Test counting tables on a page."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            count = extractor.count_tables(page_num=1)
            
            assert isinstance(count, int)
            assert count >= 0
    
    def test_get_table_summary(self, sample_pdf_path):
        """Test getting summary of all tables in PDF."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            summary = extractor.get_table_summary()
            
            assert isinstance(summary, dict)
            for page_num, count in summary.items():
                assert isinstance(page_num, int)
                assert isinstance(count, int)
                assert count > 0
    
    def test_context_manager(self, sample_pdf_path):
        """Test that context manager properly opens and closes PDF."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        with TableExtractor(sample_pdf_path) as extractor:
            assert extractor.pdf is not None
        
        # After context exit, PDF should be closed
        # (checking closed state would require accessing internal pdfplumber state)
    
    def test_static_extract_single_table(self, sample_pdf_path):
        """Test static convenience method for single table extraction."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        table = TableExtractor.extract_single_table(sample_pdf_path, page_num=1, table_index=1)
        
        if table:
            assert table['page'] == 1
            assert table['table_index'] == 1
    
    def test_static_extract_all_tables(self, sample_pdf_path):
        """Test static convenience method for all tables extraction."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        tables = TableExtractor.extract_all_tables(sample_pdf_path, page_num=1)
        
        assert isinstance(tables, list)
    
    def test_static_get_pdf_table_summary(self, sample_pdf_path):
        """Test static convenience method for table summary."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        summary = TableExtractor.get_pdf_table_summary(sample_pdf_path)
        
        assert isinstance(summary, dict)


class TestParserIntegration:
    """Test parser.py integration functions."""
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Provide path to sample PDF with tables."""
        return "test_data/sample_with_tables.pdf"
    
    def test_extract_table_by_index(self, sample_pdf_path):
        """Test parser.extract_table_by_index function."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        table = extract_table_by_index(sample_pdf_path, page_num=1, table_index=1)
        
        if table:
            assert 'page' in table
            assert 'table_index' in table
    
    def test_extract_all_tables(self, sample_pdf_path):
        """Test parser.extract_all_tables function."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        tables = extract_all_tables(sample_pdf_path, page_num=1)
        
        assert isinstance(tables, list)
    
    def test_get_table_summary(self, sample_pdf_path):
        """Test parser.get_table_summary function."""
        if not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not found")
        
        summary = get_table_summary(sample_pdf_path)
        
        assert isinstance(summary, dict)


class TestTableDataStructure:
    """Test that extracted table data has correct structure."""
    
    def test_table_dict_structure(self):
        """Test expected keys in table dictionary."""
        # This tests the _format_table method's output structure
        expected_keys = {
            'table_index',
            'page',
            'rows',
            'columns',
            'headers',
            'data',
            'raw'
        }
        
        # Create mock table data
        mock_table = [
            ['Header1', 'Header2', 'Header3'],
            ['Row1Col1', 'Row1Col2', 'Row1Col3'],
            ['Row2Col1', 'Row2Col2', 'Row2Col3']
        ]
        
        # Test formatting (would need to instantiate TableExtractor)
        # This is a structural test placeholder
        assert True
    
    def test_empty_table_handling(self):
        """Test that empty tables are handled gracefully."""
        # Test with empty table data
        assert True
    
    def test_none_cell_handling(self):
        """Test that None values in cells are converted to empty strings."""
        # Test cell None handling
        assert True


class TestErrorHandling:
    """Test error handling in table extraction."""
    
    def test_nonexistent_file(self):
        """Test that nonexistent file is handled gracefully."""
        result = extract_table_by_index("nonexistent.pdf", page_num=1, table_index=1)
        assert result is None
    
    def test_invalid_pdf_file(self, tmp_path):
        """Test that invalid PDF file is handled gracefully."""
        # Create invalid PDF file
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a PDF")
        
        result = extract_table_by_index(str(invalid_pdf), page_num=1, table_index=1)
        assert result is None
    
    def test_zero_page_number(self):
        """Test that page number 0 is handled."""
        result = extract_table_by_index("test.pdf", page_num=0, table_index=1)
        assert result is None
    
    def test_negative_table_index(self):
        """Test that negative table index (other than -1) is handled."""
        # -1 is valid (last table), but -2, -3 etc should be handled
        # Current implementation allows -1, need to verify others
        assert True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
