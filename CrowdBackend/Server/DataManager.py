import datetime
import sqlite3
from os import makedirs, path
from CrowdBackend import ServerDir
from datetime import timedelta, datetime as dt
from CrowdBackend.Utils import avg, str2Time, time2Str

sqlOnlyDate = lambda time: f"strftime('%F', {time})"
sqlOnlyTime = lambda time: f"strftime('%T', {time})"
sqlTimeInSec = lambda time: f"strftime('%s', {time})"
sqlDateInSec = lambda time: f"strftime('%s', strftime('%Y-%m-%d', {time}))"
sqlSecOfDay = lambda time: f"({sqlTimeInSec(time)} - {sqlDateInSec(time)})"
TimeZoneDrift = timedelta(hours=5, minutes=30)

class DataManager:
    defDivTimeDelta = 3600
    databaseDir = f"{ServerDir}/database"
    databasePath = f"{databaseDir}/CrowdDatabase.db"
    def __init__(self, dbName=databasePath):
        self.dbName = dbName
        self.connection = None
        self.cursor = None
        self.connectToDatabase()
        self.createTables()

    def connectToDatabase(self):
        try:
            dbDir = path.dirname(self.dbName)
            if not path.exists(dbDir): makedirs(dbDir)
            self.connection = sqlite3.connect(self.dbName, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON;")
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")

    def createTables(self):
        try:
            # Create Location table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Location (
                    Name TEXT PRIMARY KEY,
                    Address TEXT,
                    CreatedBy TEXT
                )
            ''')

            # Create Record table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Record (
                    Location TEXT,
                    AtTime DATETIME,
                    FromEmail TEXT,
                    Message TEXT,
                    PhotoPath TEXT,
                    CrowdCount INTEGER,
                    PRIMARY KEY (Location, AtTime),
                    FOREIGN KEY (Location) REFERENCES Location(Name)
                )
            ''')
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")

    def insertLocation(self, name, address, by="admin@crowd.com"):
        try:
            self.cursor.execute('''
                INSERT INTO Location (Name, Address, CreatedBy) 
                VALUES (?, ?, ?)
            ''', (name, address, by))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error inserting into Location table: {e}")

    def insertRecord(self, atLocation, atTime, fromEmail, message, photoPath, crowdAt):
        try:
            self.cursor.execute('''
                INSERT INTO Record (Location, AtTime, FromEmail, Message, PhotoPath, CrowdCount) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (atLocation, atTime, fromEmail, message, photoPath, crowdAt))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error inserting into Record table: {e}")

    def getAllLocations(self):
        try:
            self.cursor.execute('SELECT * FROM Location')
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error fetching locations: {e}")
            return []

    def isLocationIn(self, location):
        if location is not None:
            try:
                self.cursor.execute('SELECT * FROM Location WHERE Name = ?', (location, ))
                return any(self.cursor.fetchall())
            except sqlite3.Error as e:
                print(f"Error fetching locations: {e}")
        return False

    def getRecordsByLocation(self, location):
        if location is not None:
            try:
                self.cursor.execute('SELECT * FROM Record WHERE Location = ?', (location,))
                return self.cursor.fetchall()
            except sqlite3.Error as e:
                print(f"Error fetching records: {e}")
        return []

    def getAvgCrowdOf(self, location):
        if location is not None:
            try:
                self.cursor.execute(
                    '''
                        SELECT AVG(CrowdCount)
                        FROM Record
                        WHERE Location = ? AND CrowdCount >= 1
                    ''', (location,)
                )
                result = self.cursor.fetchone()
                if result and len(result) == 1 and result[0]:
                    return result[0]
            except sqlite3.Error as e: print(f"Error querying records: {e}")
        return 0

    def getCrowdAt(self, location, time):
        if isinstance(time, str): time = str2Time(time)
        # Error No enough data
        if location is None or time is None: return -1
        # Error Invalid Data
        if not self.isLocationIn(location): return -2
        timeWindowStart = time2Str(time - timedelta(minutes=60))
        timeWindowEnd = time2Str(time)
        queryDetails = {
            "WHERE Location = ? AND AtTime BETWEEN ? AND ?": (location, timeWindowStart, timeWindowEnd),
            "WHERE Location = ? AND strftime('%w', AtTime) = ? AND strftime('%H', AtTime) = ?":
                (location, str(time.weekday()+1), f"{time.hour:02d}"),
            "WHERE Location = ? AND strftime('%H', AtTime) = ?": (location, f"{time.hour:02d}"),
        }

        try:
            # Query for records within 30 minutes before and after the given time
            for idx, (condition, arg) in enumerate(queryDetails.items()):
                self.cursor.execute(
                    f'''
                        SELECT COUNT(CrowdCount), MIN(CrowdCount), MAX(CrowdCount), AVG(CrowdCount)
                        FROM Record {condition}
                    ''',  arg
                )
                result = self.cursor.fetchone()
                if result and any(result):
                    # Proper Result
                    return idx+1, *result
            # Error No Enough Records to Analyze
            return (0,)
        except sqlite3.Error as e:
            print(f"Error querying records: {e}")
            # Error RuntimeError
            return -10, e

    def getAdvCrowdDetailsAt(self, location, time):
        if isinstance(time, str): time = str2Time(time)
        # Error No enough data
        if location is None or time is None: return (-1, )
        # Error Invalid Data
        if not self.isLocationIn(location): return (-2, )
        noOfNextHrToCheck = 4; resCode = 0;
        avgCrowdOn4Hrs = 0; lowCrowdAt = -1
        crownOnN4Hrs = []

        avgCrowd = self.getAvgCrowdOf(location)
        if avgCrowd > 0:
            crownOnN4Hrs = [
                self.getCrowdAt(location, time+timedelta(hours=hr))
                for hr in range(noOfNextHrToCheck)
            ]
            avgCrowdOn4Hrs = avg([data[3] for data in crownOnN4Hrs if data[0] > 0])

            if avgCrowdOn4Hrs > 0:
                resCode = 1
                for hr, crdAtHr in enumerate(crownOnN4Hrs):
                    if crdAtHr[0] == 0: continue

                    if lowCrowdAt < 0: lowCrowdAt = hr
                    elif crdAtHr[3] < crownOnN4Hrs[lowCrowdAt][3]:
                        lowCrowdAt = hr

                if lowCrowdAt >= 0:
                    resCode = 2
        return resCode, avgCrowd, avgCrowdOn4Hrs, lowCrowdAt, crownOnN4Hrs

    def getRecordNear(self, location, time, recordWith="PhotoOnly"):
        # If photoNeeded only chooses Record with Photo,
        # Even if Record near time without photo exists
        if isinstance(time, str): time = str2Time(time)
        # Error No enough data
        if location is None or time is None: return (-1, )
        # Error Invalid Data
        if not self.isLocationIn(location): return (-2, )
        strTime = time2Str(time)
        queryDetails = {
            "WHERE Location = ?"
            "ORDER BY ABS(strftime('%s', AtTime) - strftime('%s', ?))": (location, strTime),
            "WHERE Location = ? AND strftime('%w', AtTime) = ? AND strftime('%H', AtTime) = ?":
                (location, str(time.weekday()+1), f"{time.hour:02d}"),
            "WHERE Location = ? AND strftime('%H', AtTime) = ?": (location, f"{time.hour:02d}"),
            "WHERE Location = ?": (location, ),
        }

        try:
            recordCond = ""
            if recordWith == "PhotoOnly": recordCond = "AND PhotoPath != ''"
            elif recordWith == "NoPhotoOnly": recordCond = "AND PhotoPath = ''"
            for idx, (condition, arg) in enumerate(queryDetails.items()):
                self.cursor.execute(
                    # """select atTime, crowdCount, photoPath from Record where photoPath=''"""
                    f'''
                        SELECT AtTime, PhotoPath, CrowdCount
                        FROM Record {condition} 
                        AND PhotoPath = ''
                    ''',  arg
                )
                result = self.cursor.fetchone()
                if result and any(result):
                    # Proper Result
                    return idx+1, *result
            # Error No Enough Records to Analyze
            return (0, )
        except sqlite3.Error as e:
            print(f"Error querying records: {e}")
            # Error RuntimeError
            return -10, e

    def getCrowdAtEx(self, location, time, divTimeDelta=defDivTimeDelta):
        if isinstance(time, str): time = str2Time(time)
        if location is None or time is None: return (-1, )
        if not self.isLocationIn(location): return (-2, )

        timeStr = time2Str(time)
        nearTimeWeekDay = (time.isoweekday()) % 7
        nearTimeDaySec = (timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
                          .total_seconds())
        nearTimeDaySec = int(nearTimeDaySec)
        nearTimeInDiv = nearTimeDaySec // divTimeDelta
        try:
            # Query for records within 30 minutes before and after the given time
            for queryAcc in range(3):
                typeCondition = ""
                if queryAcc == 0:
                    typeCondition = f"And {sqlOnlyDate('atTime')} = {sqlOnlyDate(f"'{timeStr}'")}"
                elif queryAcc == 1:
                    typeCondition = f"And strftime('%w', {'atTime'}) = '{nearTimeWeekDay}'"

                query = f"""
                   Select 
                       {sqlTimeInSec('atTime')}/{divTimeDelta},
                       count(crowdCount), min(crowdCount), max(crowdCount), avg(crowdCount),
                       {sqlTimeInSec('atTime')}/1, MIN(ABS({sqlSecOfDay('atTime')} - {nearTimeDaySec}))
                   From Record Where location = '{location}' {typeCondition}
                   Group by {sqlSecOfDay('atTime')}/{divTimeDelta}
                   Having {sqlSecOfDay('atTime')}/{divTimeDelta} = {nearTimeInDiv}
               ;"""
                self.cursor.execute(query)
                queryRes = self.cursor.fetchone()
                if queryRes and any(queryRes):
                    timeDiv, count, min, max, avg, nearRecordTime, withGap = queryRes
                    timeOfDiv = dt.fromtimestamp(timeDiv * divTimeDelta) - TimeZoneDrift
                    timeOfNRecord = dt.fromtimestamp(nearRecordTime) - TimeZoneDrift
                    return queryAcc + 1, timeOfDiv, count, min, max, avg, timeOfNRecord, withGap
            # Error No Enough Records to Analyze
            return (0,)
        except sqlite3.Error as e:
            print(f"Error querying records: {e}")
            # Error RuntimeError
            return -10, e

    def getRecordNearEx(self, location, time, divTimeDelta=defDivTimeDelta):
        if isinstance(time, str): time = str2Time(time)
        if location is None or time is None: return (-1, )
        if not self.isLocationIn(location): return (-2, )

        timeStr = time2Str(time)
        nearTimeDaySec = (timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
                          .total_seconds())
        nearTimeDaySec = int(nearTimeDaySec)
        nearTimeInDiv = nearTimeDaySec // divTimeDelta
        nearTimeWeekDay = (time.isoweekday()) % 7
        try:
            # Query for records within 30 minutes before and after the given time
            for queryAcc in range(3):
                typeCondition = ""
                if queryAcc == 0:
                    typeCondition = f"And {sqlOnlyDate('atTime')} = {sqlOnlyDate(f"'{timeStr}'")}"
                elif queryAcc == 1:
                    typeCondition = f"And strftime('%w', {'atTime'}) = '{nearTimeWeekDay}'"

                query = f"""
                    Select 
                        {sqlTimeInSec('atTime')}/1, PhotoPath, crowdCount,
                         MIN(ABS({sqlSecOfDay('atTime')} - {nearTimeDaySec}))
                    From Record Where location = '{location}' {typeCondition}
                    And strftime('%k', {'atTime'})/1 = {time.hour}
                    -- And {sqlOnlyDate('atTime')} = {sqlOnlyDate(f"'{timeStr}'")}
                    -- And {sqlSecOfDay('atTime')}/{divTimeDelta} = {nearTimeInDiv}
                    And PhotoPath != ''
                    -- Group by {sqlSecOfDay('atTime')}/{divTimeDelta}
                    -- Having {sqlSecOfDay('atTime')}/{divTimeDelta} = {nearTimeInDiv}
                ;"""
                self.cursor.execute(query)
                queryRes = self.cursor.fetchone()
                # print(queryRes, time.hour)
                if queryRes and any(queryRes):
                    atTime, photoPath, count, withGap = queryRes
                    timeOfRecord = dt.fromtimestamp(atTime) - TimeZoneDrift
                    return 1, timeOfRecord, photoPath, count
            # Error No Enough Records to Analyze
            return (0,)
        except sqlite3.Error as e:
            print(f"Error querying records: {e}")
            # Error RuntimeError
            return -10, e

    def getCrowdSeq(self, location, time, noOfSeq=4, divTimeDelta=defDivTimeDelta):
        if isinstance(time, str): time = str2Time(time)
        return [
            self.getCrowdAtEx(
                location, time + timedelta(seconds=seq * divTimeDelta),
                divTimeDelta=divTimeDelta
            )
            for seq in range(noOfSeq)
        ]

    def closeConnection(self):
        if self.connection:
            self.connection.close()

# Example Usage
if __name__ == "__main__":
    dataManager = DataManager()
    location = "Domlur"
    # divTimeBySecs = DataManager.defDivTimeDelta
    time = f"2024-10-16 10:00:00"

    # result = dataManager.getCrowdSeq(location, time, 24)
    # for res in result:
    #     print(*res[1:], res[0], sep=", ")
    for i in range(24):
        nearTime = f"2024-11-15 {i:02}:00:00" #dt.fromtimestamp(1732295642) # "2024-11-22 17:41:59"
        print(dataManager.getRecordNearEx(location, nearTime), nearTime)
    #     new = dataManager.getCrowdAtEx(location, nearTime)
    #     print(*new[1:], new[0], sep=", ")
    # testProto(dataManager, location, nearTime)
    dataManager.closeConnection()
