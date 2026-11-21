import win32evtlog
import win32evtlogutil
import requests

LOG_NAME = "System"
EVENT_LIMIT = 10
SERVER_URL = "http://127.0.0.1:8000/events"
EVENT_LEVELS = {
    win32evtlog.EVENTLOG_SUCCESS: "Success",
    win32evtlog.EVENTLOG_ERROR_TYPE: "Error",
    win32evtlog.EVENTLOG_WARNING_TYPE: "Warning",
    win32evtlog.EVENTLOG_INFORMATION_TYPE: "Information",
    win32evtlog.EVENTLOG_AUDIT_SUCCESS: "Audit Success",
    win32evtlog.EVENTLOG_AUDIT_FAILURE: "Audit Failure",
}

def read_windows_events():
    events = []
    handle = win32evtlog.OpenEventLog(None, LOG_NAME)
    flags = (win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ)
    try:
        while len(events) < EVENT_LIMIT:
            records = win32evtlog.ReadEventLog(handle, flags, 0)
            if not records:
                break
            for record in records:
                if len(events) >= EVENT_LIMIT:
                    break
                event_id = record.EventID & 0xFFFF
                record_number = record.RecordNumber
                source = record.SourceName
                level = EVENT_LEVELS.get(record.EventType, "Unknown")
                created_at = record.TimeGenerated.Format("%Y-%m-%d %H:%M:%S")
                message = win32evtlogutil.SafeFormatMessage(record, LOG_NAME)
                if not message or not message.strip():
                    message = f"Event {event_id} from {source}: description unavailable"
                events.append({"event_id": event_id, "record_number": record_number, "source": source, "level": level, "message": message, "created_at": created_at})
    finally:
        win32evtlog.CloseEventLog(handle)
    return events

def send_events(events: list[dict]):
    added = 0
    duplicates = 0
    for event in events:
        try:
            response = requests.post(SERVER_URL, json=event, timeout=5)
            if response.status_code == 201:
                added += 1
                print(f"Added: {event['record_number']}")
            elif response.status_code == 200:
                result = response.json()
                if result.get("status") == "duplicate":
                    duplicates += 1
                    print(f"Duplicate: {event['record_number']}")
                else:
                    print(f"Unexpected response: {response.text}")
            else:
                print(f"Error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            break
    print("\nTransmission completed")
    print(f"Added events: {added}")
    print(f"Duplicates events: {duplicates}")

def main():
    events = read_windows_events()
    if not events:
        print("No Windows events found")
        return
    events.reverse()
    print(f"Found {len(events)} Windows events\n")
    send_events(events)

if __name__ == "__main__":
    main()