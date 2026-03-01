from sqlalchemy import create_engine, desc, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

# Database connection
engine = create_engine("sqlite:///chinook.db")
Session = sessionmaker(bind=engine)

# Automatic mapping of tables
Base = automap_base()
Base.prepare(engine, reflect=True)

# Access mapped classes for querying
Customers = Base.classes.customers
Invoices = Base.classes.invoices
InvoiceItems = Base.classes.invoice_items
Tracks = Base.classes.tracks
Albums = Base.classes.albums
Artists = Base.classes.artists


def get_top_10_spending_customers():
    """Return the top 10 customers who spent the most."""
    session = Session()

    # Define columns for the query
    total_spent = func.sum(Invoices.Total).label("TotalSpent")

    # Build the query
    top_customers = (
        session.query(
            Customers.CustomerId,
            (Customers.FirstName + " " + Customers.LastName).label("CustomerName"),
            total_spent,
            func.count(Invoices.InvoiceId).label("NumberOfTransactions"),
            func.min(Invoices.InvoiceDate).label("FirstPurchase"),
            func.max(Invoices.InvoiceDate).label("LastPurchase"),
        )
        .join(Invoices, Customers.CustomerId == Invoices.CustomerId)
        .group_by(Customers.CustomerId)
        .order_by(desc(total_spent))
        .limit(10)
        .all()
    )

    session.close()
    return top_customers


def get_top_10_countries_by_revenue():
    """Return the top 10 countries with the highest revenue."""
    session = Session()

    total_revenue = func.sum(Invoices.Total).label("TotalRevenue")

    top_countries = (
        session.query(
            Invoices.BillingCountry,
            total_revenue,
            func.count(Invoices.InvoiceId).label("NumberOfSales"),
            func.count(Invoices.CustomerId.distinct()).label("UniqueCustomers"),
        )
        .group_by(Invoices.BillingCountry)
        .order_by(desc(total_revenue))
        .limit(10)
        .all()
    )

    session.close()
    return top_countries


def get_top_10_artists_by_units_sold():
    """Return the top 10 artists with the most units sold."""
    session = Session()

    total_units_sold = func.sum(InvoiceItems.Quantity).label("TotalUnitsSold")

    top_artists = (
        session.query(
            Artists.ArtistId,
            Artists.Name.label("ArtistName"),
            total_units_sold,
            func.sum(InvoiceItems.UnitPrice * InvoiceItems.Quantity).label(
                "TotalRevenue"
            ),
            func.count(Albums.AlbumId.distinct()).label("NumberOfAlbums"),
        )
        .join(Albums, Artists.ArtistId == Albums.ArtistId)
        .join(Tracks, Albums.AlbumId == Tracks.AlbumId)
        .join(InvoiceItems, Tracks.TrackId == InvoiceItems.TrackId)
        .group_by(Artists.ArtistId)
        .order_by(desc(total_units_sold))
        .limit(10)
        .all()
    )

    session.close()
    return top_artists


if __name__ == "__main__":
    print("--- Top 10 Customers who spent the most ---")
    top_customers = get_top_10_spending_customers()
    for customer in top_customers:
        print(
            f"ID: {customer.CustomerId}, "
            f"Name: {customer.CustomerName}, "
            f"Total Spent: ${customer.TotalSpent:.2f}"
        )

    print("\n--- Top 10 Countries with the highest revenue ---")
    top_countries = get_top_10_countries_by_revenue()
    for country in top_countries:
        print(
            f"Country: {country.BillingCountry}, "
            f"Revenue: ${country.TotalRevenue:.2f}, "
            f"Sales: {country.NumberOfSales}"
        )

    print("\n--- Top 10 Artists with the most units sold ---")
    top_artists = get_top_10_artists_by_units_sold()
    for artist in top_artists:
        print(
            f"Artist: {artist.ArtistName}, "
            f"Units Sold: {artist.TotalUnitsSold}, "
            f"Revenue: ${artist.TotalRevenue:.2f}"
        )
