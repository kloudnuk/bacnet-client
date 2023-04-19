# BACnet Client
The BACnet Client module uses Joel Bender's Bacpypes3 python package as its BACnet stack in order to implement a service layer with the following service interfaces:<br>
- Device discovery
- Point discovery
- Trend collection
- Real time data collection
- Event Notification
- Schedule discovery
- Firmware and application version discovery

![bacnet-client](docs/res/BACnetClient.png)

## Device Discovery
### Service Layer
Use the bacpypes3 who-is native service interface to discover bacnet devices in an Async tasks that run on an infinite loop. Design a set of DTOs (Data Transfer Objects) to capture the device information schema. Send any new device data to the in-memory database to cache it. Develop a CRUD interface for the selected in-memory database.

### Data Association Layer
Develop Object Association Dictionaries between the different entity types the service deals with (Devices-to-points, device-to-firmware, etc.). Cache the association entries in an in-memory database and push periodically to a long term database.
### Data Normalization Layer
Transforms cached device data transfer objects collected from the service layer component into the final long term database schema's data definition objects.
### Long Term Persistance (System Object Map)
Database interface for Create, Update, and Delete operations.

## Data Point Discovery
### Service Layer
### Data Clean-up Layer
### Data Association Layer
### Data Normalization Layer
### Long Term Persistance
