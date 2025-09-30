from backend.app.db.core import Base, get_engine


def run() -> None:
    print("Creating database tables...")
    engine = get_engine()
    if engine is None:
        raise RuntimeError(
            "Database engine not available - ensure DATABASE_URL is set and drivers are installed"
        )
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


if __name__ == "__main__":
    run()
