from backend.app.db.core import Base, engine

def run() -> None:
    print('Creating database tables...')
    Base.metadata.create_all(bind=engine)
    print('Database tables created successfully')


if __name__ == "__main__":
    run()
