from sqlalchemy import text
from sqlalchemy.sql import Select


def build_search_query(base_query: Select, search_term: str, dialect: str) -> Select | None:
    """Build search query based on database type.
    
    Args:
        base_query: Base SQLAlchemy query
        search_term: Term to search for
        dialect: Database dialect name ('postgresql', 'sqlite', etc)
        
    Returns:
        Modified query with search conditions or None if search not supported
    """
    if dialect != "postgresql":
        # Only PostgreSQL FTS is supported
        return None
    
    # PostgreSQL Full Text Search
    return base_query.where(
        text("search_vector @@ plainto_tsquery('english', :term)")
    ).params(term=search_term).order_by(
        text("ts_rank(search_vector, plainto_tsquery('english', :term)) DESC")
    )