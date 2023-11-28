import streamlit as st
import datetime
import uuid
import json
import paho.mqtt.client as mqtt
from sqlalchemy import create_engine, Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the base class
Base = declarative_base()

# Define the ProcessRecord class
class ProcessRecord(Base):
    __tablename__ = 'process_records'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_number = Column(Integer, nullable=False)
    todays_date = Column(DateTime, default=datetime.datetime.utcnow)
    process_start_time = Column(DateTime, nullable=False)
    process_end_time = Column(DateTime, nullable=False)
    process_duration = Column(Integer)  # Assuming storage in seconds

# Create the SQLite database
engine = create_engine('sqlite:///process_records.db')
Base.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# MQTT setup
mqtt_broker = "localhost"
mqtt_port = 1884
mqtt_client = mqtt.Client()
mqtt_client.connect(mqtt_broker, mqtt_port, 60)

# Function to publish data to MQTT
def publish_to_mqtt(topic, message):
    mqtt_client.publish(topic, message)

# Streamlit app
def main():
    st.title("Process Data Entry Form")

    # Initialize session state if not already done
    if 'process_start_date' not in st.session_state:
        st.session_state.process_start_date = datetime.date.today()
    if 'process_start_time' not in st.session_state:
        st.session_state.process_start_time = datetime.datetime.now().time()
    if 'process_end_date' not in st.session_state:
        st.session_state.process_end_date = datetime.date.today()
    if 'process_end_time' not in st.session_state:
        st.session_state.process_end_time = datetime.datetime.now().time()

    with st.form("process_form"):
        lot_number = st.number_input("Lot Number", min_value=1, step=1)
        process_start_date = st.date_input("Process Start Date", st.session_state.process_start_date)
        process_start_time = st.time_input("Process Start Time", st.session_state.process_start_time)
        process_end_date = st.date_input("Process End Date", st.session_state.process_end_date)
        process_end_time = st.time_input("Process End Time", st.session_state.process_end_time)
        submit_button = st.form_submit_button("Submit")

        if submit_button:
            # Combine date and time inputs into datetime objects
            start_datetime = datetime.datetime.combine(process_start_date, process_start_time)
            end_datetime = datetime.datetime.combine(process_end_date, process_end_time)

            # Check if the end datetime is after the start datetime
            if end_datetime <= start_datetime:
                st.error("Process End Time must be after Process Start Time.")
            else:
                process_duration = int((end_datetime - start_datetime).total_seconds())

                # Create a new record
                new_record = ProcessRecord(
                    lot_number=lot_number,
                    todays_date=datetime.datetime.utcnow(),
                    process_start_time=start_datetime,
                    process_end_time=end_datetime,
                    process_duration=process_duration
                )

                # Add new record to the session and commit to the database
                session.add(new_record)
                session.commit()

                # Publish each entry to its respective MQTT topic
                publish_to_mqtt("process_records/lot_number", json.dumps({"lot_number": lot_number}))
                publish_to_mqtt("process_records/todays_date", json.dumps({"todays_date": new_record.todays_date.isoformat()}))
                publish_to_mqtt("process_records/process_start_time", json.dumps({"process_start_time": start_datetime.isoformat()}))
                publish_to_mqtt("process_records/process_end_time", json.dumps({"process_end_time": end_datetime.isoformat()}))
                publish_to_mqtt("process_records/process_duration", json.dumps({"process_duration": process_duration}))

                st.success("Record added successfully!")

if __name__ == "__main__":
    main()
