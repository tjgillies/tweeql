from datetime import date, timedelta
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from sqlalchemy import create_engine, MetaData, select,and_, or_, not_
from sqlalchemy.sql import func
import json

# this is the database address that sqlalchemy uses to connect.
DB_URI='sqlite:////Users/badar/Desktop/UROP/ssql/test.db'
# this is the latitude/longitude grid size of squares displayed on map
GRANULARITY=1.0

def generate_style_kml():
    blue=255
    red=0
    delta=5
    linewidth=0
    list_styles=[]
    list_styles.append(generate_style('FFFF0000',0,linewidth))
    for id in range(1,52):
        blue=blue-delta
        red=red+delta
        hexa=convert_to_hex(blue,red)
        list_styles.append(generate_style(hexa,id,linewidth))
    return "".join(list_styles)
        
def convert_to_hex(blue,red):
    b=hex(blue)[2:]
    if blue<=15:
        b='0'+b
    r=hex(red)[2:]
    if red<=15:
        r='0'+r
    return 'FF'+b+'00'+r


def generate_style(hexa,id,linewidth):
    style='''    
<Style id="style%d">
  <LineStyle>
    <width>%f</width>
  </LineStyle>
  <PolyStyle>
    <color>%s</color>
  </PolyStyle>
</Style>
'''
    style = style % (id, linewidth, hexa)
    return style

def generate_placemarks_kml(temperature_table, db_conn):
    yesterday = date.today()-timedelta(hours=24)
    where_clause = and_(temperature_table.c.latitude != None,
                        temperature_table.c.longitude != None, 
                        temperature_table.c.temperature != None,
                        temperature_table.c.temperature > 0.0,
                        temperature_table.c.temperature < 120.0, 
                        temperature_table.c.created_at > yesterday)
    data_query = select([func.round(temperature_table.c.latitude).label('latitude'),
                         func.round(temperature_table.c.longitude).label('longitude'),
                         func.avg(temperature_table.c.temperature).label('temperature')],where_clause).\
                         group_by(func.round(temperature_table.c.latitude),func.round(temperature_table.c.latitude))
    maxT_query = select([func.max(temperature_table.c.temperature)], where_clause)
    minT_query = select([func.min(temperature_table.c.temperature)], where_clause)

    minT_result = db_conn.execute(minT_query)
    minT = minT_result.scalar()
    minT_result.close()
    maxT_result = db_conn.execute(maxT_query)
    maxT = maxT_result.scalar()
    maxT_result.close()
    deltaT = maxT-minT
    a = (51/deltaT)
    
    list_placemarks=[]
    cursor = db_conn.execute(data_query) 
    for row in cursor:
        p=float(row["temperature"])-minT
        normalize_temp=a*p
        color=round(normalize_temp)
        latlng=lat_lng(row)
        list_placemarks.append(generate_placemarks(row,color,latlng))
    cursor.close()
    return "".join(list_placemarks)


def lat_lng(row):
    """
        Calculates the (lat,lon) of the four points of the square grid based on the granularity
        that is colored and displayed on google maps. For example, point (20.3,20) with a granularity 
        of 0.5 will have points [(20,20),(20,20.5),(20.5,20.5),(20.5,20)]. 
    """
    lat = row["latitude"]
    lng = row["longitude"]
    n = int(lat/GRANULARITY)
    nlat_start = n * GRANULARITY
    nlat_end = nlat_start + GRANULARITY
    nlg=int(lng/GRANULARITY)
    nlng_start = nlg * GRANULARITY
    nlng_end = nlng_start + GRANULARITY
    latlng=[(nlat_start,nlng_start), (nlat_start,nlng_end), (nlat_end,nlng_end), (nlat_end,nlng_start)]
    return latlng

def generate_placemarks(row,color,latlng):
    placemark='''   
<Placemark>
<name>%s</name>
    <styleUrl>#style%d</styleUrl>
<Polygon>
  <extrude>1</extrude>
  <altitudeMode>relativeToGround</altitudeMode>
  <outerBoundaryIs>
    <LinearRing>
      <coordinates>
        %f,%f,20
        %f,%f,20
        %f,%f,20
        %f,%f,20
      </coordinates>
    </LinearRing>
  </outerBoundaryIs>
  
</Polygon>
</Placemark>
'''
    placemark=placemark % (row["temperature"], color,
                           latlng[0][1], latlng[0][0], latlng[1][1], latlng[1][0],
                           latlng[2][1], latlng[2][0], latlng[3][1], latlng[3][0])
    return placemark

def begin_kml():
    
    begin='''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
'''
    return begin



def end_kml():
    end='''
</Document>
</kml>'''
    return end
    
def generate_weather_kml():
    engine = create_engine(DB_URI, echo=False)
    meta = MetaData()
    meta.reflect(bind=engine)
    temperature = meta.tables['tester2']
    conn = engine.connect()
    
    kml_body = [begin_kml(),generate_style_kml(),generate_placemarks_kml(temperature, conn), end_kml()]
    return "".join(kml_body)

def display(request):
    return HttpResponse(generate_weather_kml(),content_type="application\vnd.google-earth.kml+xml")
    
    

    
    
