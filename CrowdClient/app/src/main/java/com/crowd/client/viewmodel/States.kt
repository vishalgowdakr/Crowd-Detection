package com.crowd.client.viewmodel

import androidx.annotation.DrawableRes
import androidx.compose.runtime.Stable
import androidx.compose.ui.graphics.ImageBitmap
import com.crowd.client.R

interface PicType {
    val picDescription: String
}
data class ResPicOfPlace(
    @DrawableRes val image: Int = R.drawable.t1,
    override val picDescription: String = "Acharya Canteen at 10pm"
): PicType
@Stable
data class BitPicOfPlace(
    val image: ImageBitmap,
    override val picDescription: String
): PicType

sealed class EstResult {
    abstract val message: String
    abstract val message2: String
}

data class EstFailed(
    override val message: String = "Can't Reach Server!",
    override val message2: String = "Please try again later!"
): EstResult()

data class EstSuccess(
    val forQuery: Query = Query.fromTime(),
    val picAtQuery: PicType = ResPicOfPlace(),
    val crowdAtQuery: Int = 0,
    val crowdIs: String = "Low",
    val timeToGo: String = "5:30pm",
    val leastCrowdAt: String = "9am",
    override val message: String = "Crowd at Location \nis Estimated!",
    override val message2: String = "Please wait for details!"
): EstResult()


data class Query(
    val place: String, val dateInMillis: Long,
    val hour: Int, val minute: Int
) {
    companion object {
        fun fromTime(
            place: String = "No Location Available",
            time: Long = System.currentTimeMillis()
        ): Query {
            val date = java.util.Date(time)
            return Query(place, time, date.hours, date.minutes)
        }
    }

    val timeInMillis get() = (dateInMillis+((hour-5.5)*3600000)+(minute*60000)).toLong()
//    val timeInMillis get() = Calendar.getInstance().also {
//        val date = java.util.Date(dateInMillis)
//        it.set(date.year, date.month, date.day, hour, minute, 0)
//    }.timeInMillis
}