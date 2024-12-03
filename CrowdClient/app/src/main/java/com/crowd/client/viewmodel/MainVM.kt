package com.crowd.client.viewmodel

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.crowd.client.R
import com.crowd.client.application.AppData
import com.crowd.client.application.MainApplication
import com.crowd.client.network.CrowdApi
import com.crowd.client.network.base642Image
import com.crowd.client.network.handle
import com.crowd.client.utils.android.makeToast
import com.crowd.client.utils.str2Time
import com.crowd.client.utils.time2HtStr
import com.crowd.client.utils.time2OtStr
import com.crowd.client.utils.timeStamp2HtStr
import com.crowd.client.utils.timeStamp2OtStr
import com.crowd.client.utils.timeStamp2Str
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Date

enum class Fragment {
    StartFrag, UserFrag, QueryFrag,
    LoadingFrag, ResultPage
}

class MainVM: ViewModel(), MainApplication.AppCompanion {
    override fun initialize(context: Context) {

    }

    val crowdDenseList = listOf("Low", "Medium", "High", "Very High")
    val crowdPicList = listOf(R.drawable.t1, R.drawable.t2, R.drawable.t3, R.drawable.t4)
    val coScope = CoroutineScope(Dispatchers.IO + viewModelScope.coroutineContext)
    var onFragment by mutableStateOf(Fragment.StartFrag); private set

    var queryLastMade: Query = AppData.lastQuery ?: Query.fromTime()
        private set
    var estimationResult: EstResult = EstFailed(); private set
    var isWaitingForResult by mutableStateOf(true); private set
//    var estimationResult: EstResult by mutableStateOf(EstFailed()); private set

    fun checkAndLog() {
        onFragment = when {
            !CrowdApi.isServerReachable() ->
                Fragment.StartFrag
            !AppData.isLoggedIn -> Fragment.UserFrag
            else -> Fragment.QueryFrag
        }
    }
    fun handelAction(action: UiAction, context: Context?) {
//        println("\nonAction Called($action) at ${System.currentTimeMillis()}")
        when(action) {
            is EnterApp -> if(onFragment == Fragment.StartFrag) checkAndLog()
            is SaveUser -> if(onFragment == Fragment.UserFrag) when {
                action.user.name.isBlank() -> context?.makeToast("Name is Blank!")
                action.user.email.isBlank() -> context?.makeToast("Email is Blank!")
                else -> {
                    // Save user
                    AppData.user = action.user
                    checkAndLog()
                }
            }
            is GetEstimation -> if(onFragment == Fragment.QueryFrag) when {
                action.query.place.isBlank() -> context?.makeToast("Location is Blank!")
                action.query.timeInMillis == 0L -> context?.makeToast("Enter the Date Time!")
//                    query.atDate == null -> context?.makeToast("Enter the Date!")
//                    query.atTime == null -> context?.makeToast("Enter the Time!")
                else -> {
                    isWaitingForResult = true
                    onFragment = Fragment.LoadingFrag
                    queryLastMade = action.query
                    AppData.lastQuery = queryLastMade

                    coScope.launch {
                        estimationResult = processQuery(queryLastMade)
                        delay(1000)
                        isWaitingForResult = false
                        if(estimationResult is EstSuccess) {
                            delay(1000)
                            onFragment = Fragment.ResultPage
                        }
                    }
                }
            }
            is GoBack -> checkAndLog()
        }
    }

    suspend fun getPhotoNear(location: String, strTime: String): Triple<String, Bitmap, Int>? {
        CrowdApi.getPhotoNear(location, strTime).await()?.apply {
            if(code() == 200) {
                val recordTime = body()?.get("recordTime") as String
                val photo = base642Image(body()?.get("photo") as String) ?: return null
                val crowdInPhoto = (body()?.get("crowdInPhoto") as Double).toInt()
                return Triple(recordTime, photo, crowdInPhoto)
            }
        }
        return null
    }

    suspend fun processQuery(query: Query): EstResult {
        val timeInStr = timeStamp2Str(query.timeInMillis)
//        val timeInStr = timeStamp2Str(query.dateInMillis+(query.hour*3600000)+(query.minute*60000))
        println("$query $timeInStr ${timeStamp2Str(query.timeInMillis)}")
        CrowdApi.getCrowdSeq(query.place, timeInStr, 24).await()?.handle(
            onResponse = { code, _, data ->
                return when {
                    code == 200 || code == 206 -> {
                        val crowdAtSeq = data["crowdAtSeq"] as List<*>
                        var tripleData: Triple<Date, Float, Date>? = null
                        var shTrmLeastCrowdIs = 500f
                        var oAllLeastCrowdAt = 0; var oAllLeastCrowdIs = 500f
                        crowdAtSeq.forEachIndexed { idx, crowdAt ->
                            crowdAt as List<*>
                            println("$idx: $crowdAt")
                            try{
                                val crowdAcc = ((crowdAt)[0] as Double).toInt()
                                val avgCrowd = ((crowdAt)[5] as Double).toFloat()
                                if(idx < 4 && crowdAcc >= 1) {
                                    if (avgCrowd < shTrmLeastCrowdIs) {
                                        shTrmLeastCrowdIs = avgCrowd
                                        val divTime = str2Time(crowdAt[1] as String)!!
                                        val nRecordTime = str2Time(crowdAt[6] as String)!!
                                        tripleData = Triple(divTime, avgCrowd, nRecordTime)
                                    }
                                }
                                if(crowdAcc >= 1 && avgCrowd < oAllLeastCrowdIs) {
                                    oAllLeastCrowdAt = idx
                                    oAllLeastCrowdIs = avgCrowd
                                }
                            }
                            catch (e: Exception) { e.printStackTrace() }
                        }

                        if(tripleData != null) {
//                            val nowCrowdSeq = crowdAtSeq[0] as List<*>
//                            val nowCrowd = (nowCrowdSeq[5] as Double).toInt()
                            val (recordTime ,nowPhoto, crowdInPhoto) = getPhotoNear(
                                query.place, timeInStr
                            )!!

                            println("$recordTime $nowPhoto, $crowdInPhoto")
                            val (divTime, avgCrowd, nRecTime) = tripleData!!
                            val oAllLeastCrowdDiv = str2Time(
                                (crowdAtSeq[oAllLeastCrowdAt] as List<*>)[1]
                                        as String
                            ) as Date
                            val crowdStatus = when {
                                crowdInPhoto <= shTrmLeastCrowdIs -> "Low"
                                crowdInPhoto/shTrmLeastCrowdIs < 1.5f -> "Medium"
                                else -> "High"
                            }
                            val diffInDiv = System.currentTimeMillis() - divTime.time
                            val time2Go = if(diffInDiv in 0..3599999)
                                "now" else "between ${time2HtStr(divTime)} to" +
                                    " ${timeStamp2HtStr(divTime.time+3600000)}"
//                            println("$diffInDiv $time2Go")

                            val queryTime = Date(query.timeInMillis)
                            val photoTime = str2Time(recordTime)!!
                            val picDesc = "${query.place} at ${time2OtStr(photoTime)}"
                            if(
//                                queryTime.date == photoTime.date &&
                                queryTime.hours == photoTime.hours
                            ) return EstSuccess(
                                query, BitPicOfPlace(nowPhoto.asImageBitmap(), picDesc),
                                crowdInPhoto, crowdStatus, time2Go,
                                time2HtStr(oAllLeastCrowdDiv),
                            )
                        }
                        return EstFailed(
                            "No Data on Time!",
                            "Try aging with, Some other Time!"
                        )
                    }
                    code == 222 -> EstFailed(
                        "No Data on Location!",
                        "Try aging with, Some other Location!"
                    )
                    code == 404 -> EstFailed(
                        "Invalid Location!",
                        "Try aging with another Location!"
                    )
                    else -> EstFailed("Unexpected Error!")
                }
            },
            onErrorHandling = { code, e ->
                e.printStackTrace()
                return EstFailed("Parsing Error!")
            }
        )
        return EstFailed()
    }
}