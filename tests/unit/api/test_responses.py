"""
Unit tests for the API response formatting module.
"""

import pytest
from fastapi import status

from core.api.responses import (
    Meta, Pagination, Links, StandardResponse,
    create_response, create_success_response,
    create_list_response, create_created_response,
    create_no_content_response
)

@pytest.mark.unit
@pytest.mark.api
class TestAPIResponses:
    """Tests for the API response formatting module."""
    
    def test_meta_model(self):
        """Test the Meta model."""
        meta = Meta(request_id="test-request-id")
        
        assert meta.version == "1.0"
        assert meta.request_id == "test-request-id"
        assert meta.timestamp is not None
    
    def test_pagination_model(self):
        """Test the Pagination model."""
        pagination = Pagination(
            page=1,
            page_size=10,
            total_items=100,
            total_pages=10,
            has_next=True,
            has_prev=False
        )
        
        assert pagination.page == 1
        assert pagination.page_size == 10
        assert pagination.total_items == 100
        assert pagination.total_pages == 10
        assert pagination.has_next is True
        assert pagination.has_prev is False
    
    def test_links_model(self):
        """Test the Links model."""
        links = Links(
            self="/api/items",
            next="/api/items?page=2",
            prev=None,
            first="/api/items?page=1",
            last="/api/items?page=10"
        )
        
        assert links.self == "/api/items"
        assert links.next == "/api/items?page=2"
        assert links.prev is None
        assert links.first == "/api/items?page=1"
        assert links.last == "/api/items?page=10"
    
    def test_standard_response_model(self):
        """Test the StandardResponse model."""
        response = StandardResponse[dict](
            status="success",
            data={"key": "value"},
            meta=Meta(request_id="test-request-id"),
            links=Links(self="/api/items"),
            pagination=Pagination(
                page=1,
                page_size=10,
                total_items=100,
                total_pages=10,
                has_next=True,
                has_prev=False
            )
        )
        
        assert response.status == "success"
        assert response.data == {"key": "value"}
        assert response.meta.request_id == "test-request-id"
        assert response.links.self == "/api/items"
        assert response.pagination.page == 1
    
    def test_create_response(self):
        """Test the create_response function."""
        response = create_response(
            data={"key": "value"},
            status="success",
            meta={"request_id": "test-request-id"},
            links={"self": "/api/items"},
            pagination={"page": 1, "total_items": 100},
            status_code=status.HTTP_200_OK,
            request_id="test-request-id"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.body is not None
        
        # Without data
        response = create_response(
            status="success",
            status_code=status.HTTP_204_NO_CONTENT
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_create_success_response(self):
        """Test the create_success_response function."""
        response = create_success_response(
            data={"key": "value"},
            request_id="test-request-id"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.body is not None
    
    def test_create_list_response(self):
        """Test the create_list_response function."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        response = create_list_response(
            items=items,
            page=1,
            page_size=10,
            total_items=3,
            base_url="/api/items",
            request_id="test-request-id"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.body is not None
        
        # Without base_url
        response = create_list_response(
            items=items,
            page=1,
            page_size=10,
            total_items=3,
            request_id="test-request-id"
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_create_created_response(self):
        """Test the create_created_response function."""
        response = create_created_response(
            data={"id": 1, "name": "Test"},
            location="/api/items/1",
            request_id="test-request-id"
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers.get("Location") == "/api/items/1"
        assert response.body is not None
        
        # Without location
        response = create_created_response(
            data={"id": 1, "name": "Test"},
            request_id="test-request-id"
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert "Location" not in response.headers
    
    def test_create_no_content_response(self):
        """Test the create_no_content_response function."""
        response = create_no_content_response()
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.body is None

