import base64
import os
from datetime import timedelta

from flask import Flask, request
from flask_restful import Api, Resource

from CrowdDetector import crowdDetector
from CrowdBackend.Utils import response, time2Str, str2Time, saveImage, fixAndRespond
from DataManager import DataManager

# Initialize Flask and Flask-RESTful
app = Flask(__name__)
api = Api(app)

# Initialize DataManager
dataManager = DataManager()

# Resource for /getLocations (GET)
class GetLocations(Resource):
    def get(self):
        try:
            # Fetch all locations from the database
            locations = dataManager.getAllLocations()
            # Extract only the location names
            allLocations = [location[0] for location in locations]
            return response(200, message="Done!", allLocations=allLocations)
        except Exception as e:
            return response(500, error=str(e))


# Resource for /createLocation (POST)
class CreateLocation(Resource):
    def post(self):
        try:
            # Get input from request
            data = request.json
            place = data.get('place')
            address = data.get('address')

            if not all([place, address]):
                return response(400, error="Place and address are required!")
            elif dataManager.isLocationIn(place):
                return response(482, message="Location already exists!", place=place)

            # Insert the location into the database
            dataManager.insertLocation(place, address)
            return response(201, message="Location created!")
        except Exception as e:
            return response(500, error=str(e))


# Resource for /postCrowdAt (POST)
class PostCrowdAt(Resource):
    def post(self):
        try:
            # Get input from request
            data = request.json
            atLocation = data.get('atLocation')
            atTime = data.get('atTime')
            fromMail = data.get('fromMail')
            postMessage = data.get('message')
            encodedPhoto = data.get('photo')
            crowdAt = data.get('crowdAt')
            try: photoBytes = base64.b64decode(encodedPhoto)
            except: photoBytes = None

            print(atLocation, atTime, fromMail)
            if not all([atLocation, atTime, fromMail]):
                return response(400, error="Some inputs are missing!")
            if not dataManager.isLocationIn(atLocation):
                return response(404, error="Location not found!")

            status, error, message, data = 0, "", "", {}
            if photoBytes is not None:
                # Save the image (as an example, saving the image to a folder)
                locPath = f"{DataManager.databaseDir}/{atLocation}"
                if not os.path.exists(locPath): os.makedirs(locPath)
                photoPath = f"{DataManager.databaseDir}/{atLocation}/{atTime}.jpg"
                if not saveImage(photoBytes, photoPath):
                    photoPath = ""
            else: photoPath = ""
            if crowdAt is None or crowdAt < 0:
                if photoBytes:
                    crowdAt = len(crowdDetector.detectFromPath(photoPath))
            if crowdAt >= 0:
                dataManager.insertRecord(
                    atLocation, atTime, fromMail, postMessage,
                    photoPath, crowdAt
                )
                data = {"crowdDetected": crowdAt}
                status, message = 202, "Crowd record added!"
            else: status, error = 400, "No CrowdCount Given and No Proper Photo also Given to detect from!"

            return fixAndRespond(status, message, error, data)
        except Exception as e:
            # e.with_traceback()
            return response(500, error=str(e))


# Resource for /getEstimation (GET)
class GetEstimation(Resource):
    def get(self):
        try:
            args = request.args
            atLocation = args.get('atLocation')
            atTime = args.get('atTime')

            if not all([atLocation, atTime]):
                return response(400, error="Some inputs are missing!")
            # if not dataManager.isLocationIn(atLocation):
            #     return response(404, error="Location not found!")

            # Fetch advanced crowd details from DataManager
            result = dataManager.getAdvCrowdDetailsAt(atLocation, atTime)
            status, error, message, data = 0, "", "", {}
            if result[0] < 0:
                if result[0] == -1: status, error = 400, "No Proper Input!"
                elif result[0] == -2: status, error = 404, "Unavailable Location!"
                elif result[0] == -10: status, error = 500, f"Error on Query!(${result[1]})"
            else:
                resCode, avgCrowd, avgCrowdOn4Hrs, lowCrowdAt, crownOnN4Hrs = result
                atTimeInTime = str2Time(atTime)
                bestTime = atTimeInTime + timedelta(hours=lowCrowdAt)
                # diff = avgCrowdOn4Hrs / avgCrowd
                # diff = avgCrowd / avgCrowdOn4Hrs
                data = {"avgCrowd": avgCrowd, "avgCrowdOnNext4Hrs": avgCrowdOn4Hrs, "lowCrowdAtHour": lowCrowdAt,
                    "lowCrowdTime": time2Str(bestTime), "detailsNext4Hrs": crownOnN4Hrs
                }
                if result[0] == 0:
                    status = 206
                    message = "No information on Given time!"
                else:
                    status = 200
                    if avgCrowdOn4Hrs > avgCrowd:
                        message = f"For the given time Crowd could be higher than usual!"
                    else: message = f"For the given time Crowd should be lower than usual!"
                    bestTimeStr = "now" if lowCrowdAt == 0 else bestTime.strftime("%-I%p")
                    message += f"\n and {bestTimeStr} is the best time to go!"
            return fixAndRespond(status, message, error, data)
        except Exception as e:
            # e.with_traceback()
            return response(500, error=f"Unexpected Error({e})!")

# Resource for /getPhotoNear (GET)
class GetPhotoNear(Resource):
    def get(self):
        try:
            args = request.args
            atLocation = args.get('atLocation')
            atTime = args.get('atTime')
            recordWith = args.get('recordWith')
            if not recordWith: recordWith = "PhotoOnly"
            if not all([atLocation, atTime]):
                return fixAndRespond(400, error="Some inputs are missing!")

            # Query the database for the nearest record with an image
            status, error, message, data = 0, "", "", {}
            result = dataManager.getRecordNearEx(atLocation, atTime)
            if result[0] < 0:
                if result[0] == -1: status, error = 400, "No Proper Input!"
                elif result[0] == -2: status, error = 404, "Location Unavailable!"
                elif result[0] == -10: status, error = 500, f"Error on Query!(${result[1]})"
            elif result[0] == 0: status, message = 222, "Have No enough information Given Location!"
            else:
                encodedPhoto = None
                status, message = 200, "Done!"
                resCode, recordTime, photoPath, crowdCount = result
                try:
                    with open(photoPath, "rb") as photoFile:
                        encodedPhoto = base64.b64encode(photoFile.read()).decode("utf-8")
                except: pass
                if not encodedPhoto:
                    status = 206
                    if photoPath: message = "Can't find Photo!"
                    else: message = "Done with no Photo!"
                data = {"accCode": resCode, "recordTime": time2Str(recordTime), "photo": encodedPhoto, "crowdInPhoto": crowdCount}
            # print(atLocation, status, message, error, data)
            return fixAndRespond(status, message, error, data)
        except Exception as e:
            # e.with_traceback()
            return response(500, error=str(e))


# Resource for /getPhotoNear (GET)
class GetCrowdSeq(Resource):
    def get(self):
        try:
            args = request.args
            atLocation = args.get('atLocation')
            atTime = args.get('atTime')
            noOfSeq = int(args.get('noOfSeq'))
            if not noOfSeq: noOfSeq = 1

            # print(atLocation, atTime, noOfSeq)
            if not all([atLocation, atTime, noOfSeq]):
                return fixAndRespond(400, error="Some inputs are missing!")
            if not dataManager.isLocationIn(atLocation):
                return response(404, error="Location not found!")

            # Query the database for the nearest record with an image
            status, error, message, data = 0, "", "", {}
            crowdSeq = dataManager.getCrowdSeq(atLocation, atTime, noOfSeq)
            processedSeq = []
            hasData, isAnyZero = False, False
            for crowdRes in crowdSeq:
                processedRes = list(crowdRes)
                if crowdRes[0] < -1:
                    if crowdRes[0] == -1: status, error = 400, "No Proper Input!"
                    elif crowdRes[0] == -2: status, error = 404, "Unavailable Location!"
                    elif crowdRes[0] == -10: status, error = 500, f"Error on Query!(${crowdRes[1]})"
                    break
                elif crowdRes[0] == 0: isAnyZero = True
                else:
                    hasData = True
                    processedRes[1] = time2Str(processedRes[1])
                    processedRes[6] = time2Str(processedRes[6])
                processedSeq.append(processedRes)
            else:
                if not hasData:
                    status, message = 222, "Have No enough information Given Location!"
                elif isAnyZero:
                    status, message = 206, "Contains some TimeDiv with no data!"
                else:
                    status, message = 200, "Done!"
                data = {"crowdAtSeq": processedSeq}
            # print(atLocation, status, message, error, data)
            return fixAndRespond(status, message, error, data)
        except Exception as e:
            e.with_traceback()
            return response(500, error=str(e))

# Adding routes/endpoints to the API
# Status(200) Means: Done
# Status(201) Means: Created
# Status(202) Means: Accepted
# Status(206) Means: Partially done
# Status(222) Means: No Enough Info On Requested Data
# Status(400) Means: Bad Request
# Status(404) Means: Requested Invalid Data
# Status(500) Means: Internal Error
api.add_resource(GetLocations, '/getLocations')
api.add_resource(CreateLocation, '/createLocation')
api.add_resource(PostCrowdAt, '/postCrowdAt')
api.add_resource(GetEstimation, '/getEstimation')
api.add_resource(GetPhotoNear, '/getPhotoNear')
api.add_resource(GetCrowdSeq, '/getCrowdSeq')


if __name__ == '__main__':
    # Start the Flask server
    app.run(debug=True, host="0.0.0.0")
