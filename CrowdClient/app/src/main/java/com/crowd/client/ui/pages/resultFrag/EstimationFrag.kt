package com.crowd.client.ui.pages.resultFrag

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ShapeDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.crowd.client.ui.pages.common.components.AppButton
import com.crowd.client.ui.pages.mainPage.components.Background
import com.crowd.client.ui.theme.CrowdClientTheme
import com.crowd.client.viewmodel.BitPicOfPlace
import com.crowd.client.viewmodel.EstSuccess
import com.crowd.client.viewmodel.ResPicOfPlace


@Composable
fun EstimationFrag(
    modifier: Modifier = Modifier,
    estRes: EstSuccess = EstSuccess(),
//    picData: PicOfPlace = PicOfPlace(R.drawable.t1, "Acharya Canteen at 10pm"),
//    crowdIs: String = "low",
//    timeToGo: String = "5:30pm",
//    leastCrowdAt: String = "9am",
    onGoBack: () -> Unit = {}
) {
    Box(
        modifier
            .background(MaterialTheme.colorScheme.primaryContainer)
            .padding(10.dp, 50.dp, 10.dp, 10.dp),
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Estimated Result",
                style = MaterialTheme.typography.headlineLarge.copy(

                    textDecoration = TextDecoration.Underline,
                ),
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                modifier = Modifier.padding(top = 30.dp)
            )
//            Text(
//                text = buildAnnotatedString {
//                    append("Request is at ")
//                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
//                        append(estSuccess.forQuery.place)
//                    }
//                    append("\nat the Time ")
//                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
//                        append(timeStamp2SStr(estSuccess.forQuery.timeInMillis))
//                    }
//                },
//                style = MaterialTheme.typography.titleSmall,
//                color = MaterialTheme.colorScheme.onPrimaryContainer,
//                textAlign = TextAlign.Center,
//                modifier = Modifier.padding(top = 15.dp)
//            )

            Text(
                text = buildAnnotatedString {
                    append("According to our estimations, Crowd at\n the Given time in ")
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        append(estRes.forQuery.place)
                    }
                    append(" is ")
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        append(estRes.crowdIs)
                    }
                },
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 15.dp)
            )
            Text(
                text = buildAnnotatedString {
                    append("Crowd Count: ")
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        append("${estRes.crowdAtQuery}")
                    }
                },
                style = MaterialTheme.typography.titleLarge.copy(
                    fontWeight = FontWeight.Medium, fontSize = 25.sp,
//                    textDecoration = TextDecoration.Underline,
                ),
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 0.dp)
            )

            estRes.picAtQuery.let { pic ->
                when(pic) {
                    is ResPicOfPlace -> Image(
                        painter = painterResource(id = pic.image),
                        contentDescription = pic.picDescription,
                        modifier = Modifier
                            .padding(top = 5.dp)
                            .clip(ShapeDefaults.Small)
                    )
                    is BitPicOfPlace -> Image(
                        bitmap = pic.image,
                        contentDescription = pic.picDescription,
                        modifier = Modifier
                            .padding(top = 5.dp)
                            .clip(ShapeDefaults.Small)
                    )
                    else -> {}
                }
            }

            Text(
                text = estRes.picAtQuery.picDescription,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 7.dp)
            )

            Text(
                text = "Recommendation",
                style = MaterialTheme.typography.headlineLarge.copy(textDecoration = TextDecoration.Underline),
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 1f),
                modifier = Modifier.padding(top = 40.dp)
            )
            Text(
                text = buildAnnotatedString {
                    if(estRes.timeToGo == "now")
                        append("It is a good choice to go now!")
                    else {
                        append("According to our estimation the Best time\n to visit is ")
                        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                            append(estRes.timeToGo)
                        }
//                        append(",\nas it's when Crowd lowest!")
                    }
                },
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 15.dp)
            )

            Text(
                text = buildAnnotatedString {
                    append("And, ")
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        append(estRes.leastCrowdAt)
                    }
                    append(" is the Average time with \nLeast Crowd on any given day!")
                },
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 10.dp)
            )
        }


        AppButton(
            text = "Go Back",
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 80.dp)
                .fillMaxWidth(0.7f)
                .height(60.dp),
            onClick = onGoBack
        )
    }
}

@Preview(backgroundColor = 0xFF000000)
@Composable
private fun Preview() {
    CrowdClientTheme {
        Background(Modifier.fillMaxSize())
        EstimationFrag(
            Modifier.fillMaxSize(),
        )
    }
}