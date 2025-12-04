#!/usr/bin/env python
import requests
import json

def test_pagination():
    base_url = "http://127.0.0.1:8000/api/blogs/"
    
    print("=== Blog Pagination Test ===\n")
    
    # Test different page sizes
    page_sizes = [3, 6, 9, 12]
    
    for page_size in page_sizes:
        print(f"Testing with page_size={page_size}")
        url = f"{base_url}?page=1&page_size={page_size}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Total blogs: {data['count']}")
                print(f"  ✓ Total pages: {data['total_pages']}")
                print(f"  ✓ Current page: {data['current_page']}")
                print(f"  ✓ Page size: {data['page_size']}")
                print(f"  ✓ Has next: {data['has_next']}")
                print(f"  ✓ Has previous: {data['has_previous']}")
                print(f"  ✓ Results count: {len(data['results'])}")
                
                # Test navigation
                if data['has_next']:
                    next_response = requests.get(f"{base_url}?page=2&page_size={page_size}")
                    if next_response.status_code == 200:
                        next_data = next_response.json()
                        print(f"  ✓ Page 2 results: {len(next_data['results'])}")
                    
                print()
            else:
                print(f"  ❌ Error: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
    
    # Test filtering with pagination
    print("Testing filtering with pagination:")
    try:
        # Test search with pagination
        search_url = f"{base_url}?search=blog&page=1&page_size=6"
        response = requests.get(search_url)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Search results: {len(data['results'])} blogs with 'blog' in title/content")
            print(f"  ✓ Total matching: {data['count']}")
        
        # Test sorting with pagination
        sort_url = f"{base_url}?ordering=-likes_count&page=1&page_size=6"
        response = requests.get(sort_url)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Sorted by likes: {len(data['results'])} blogs (most liked first)")
            if data['results']:
                first_blog = data['results'][0]
                print(f"  ✓ Top blog: '{first_blog['title']}' with {first_blog['likes_count']} likes")
        
    except Exception as e:
        print(f"  ❌ Filtering test failed: {str(e)}")
    
    print("\n=== Pagination Test Complete ===")

if __name__ == "__main__":
    test_pagination()