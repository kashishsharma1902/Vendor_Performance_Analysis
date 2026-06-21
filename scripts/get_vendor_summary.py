import sqlite3
import pandas as pd
import logging
from ingestion_db import ingest_db

logging.basicConfig(
    filename="los/get_vendor_summary.log",
    level=logging.DEBUG,
    format="%(asctime)s -%(levelname)s -%(message)s",
    filemode="a"
)

def create_vendor_summary(conn):
'''this function will merge the different tables to get the overall vendor summary and adding new columns in the resultant data'''
    vendor_sales_summary = pd.read_sql_query(""" WITH FreightSummary as (
        select
            VendorNumber,
            SUM(Freight) as FreightCost
        From vendor_invoice
        Group BY VendorNumber
    ),
    
    PurchaseSummary as(
        select
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Volume,
            pp.Price as ActualPrice,
            SUM(p.Quantity) as TotalPurchaseQuantity,
            SUM(p.Dollars) as TotalPurchaseDollars
        from purchases p
        join purchase_prices pp
            on p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, pp.Price, pp.Volume
    ),
    
    SalesSummary as(
        select
            VendorNo,
            Brand,
            SUM(SalesDollars) as TotalSalesDollars,
            SUM(SalesPrice) as TotalSalesPrice,
            SUM(SalesQuantity) as TotalSalesQuantity,
            SUM(ExciseTax) as TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )
    
    select
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.Volume,
        ps.ActualPrice,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalSalesQuantity,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber= ss.VendorNo
        AND ps.Brand= ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC""",conn)

    return vendor_sales_summary


def clean_data(df):
    '''this function will clean the data'''
    #changing datatype to float
    df['Volume'] =df['Volume'].astype('float')

    #filling missing values with 0
    df.fillna(0,inplace =True)
    
    #removing spaces from categorical columns
    df['VendorName'] =df['VendorName'].str.strip()
    df['Description'] =df['Description'].str.strip()

    #creating new columns for beter analytics
    df['GrossProfit'] =df['TotalSalesDollars'] - df['ToralPurchaseDollars']
    df['ProfitMargin'] =(df['GrossProfit'] / df['TotalSalesDollars'])*100
    df['StockTurnover'] = df['TotalSalesQuantity'] /df['ToralPurchaseQuantity']
    df['SalestoPutchaseRatio'] =df['TotalSalesDollars']/df['totalPurchaseDollars']
    
    return df

if __name__ == '__main__':
    # creating database connection
    conn = sqlite3.connect('inventory.db')
    
    logging.info('Creating Vendor Summary Table.....')
    summary_df = create_vendor_summary(conn)
    logging.info(summary_df.head())
    
    logging.info('Cleaning Data.....')
    clean_df=clean_data(summary_df)
    logging.info(clean_df.head())
    
    logging.info('Ingesting data.....')
    ingest_db(clean_df, 'vendor_sales_summary', conn)
    logging.info('Completed')
        


    