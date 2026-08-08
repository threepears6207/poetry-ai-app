package uts.sdk.modules.shiyaImageAnalysis

import android.content.Context
import com.vivo.aisdk.cms.local.CmsLocalFrame
import com.vivo.aisdk.cms.local.IInitializeListener
import com.vivo.aisdk.cms.local.internal.CommApiCallBack
import com.vivo.aisdk.cms.local.internal.ResponseResult
import com.vivo.llmsdk.LlmManager
import com.vivo.llmsdk.TokenCallback

/**
 * Keeps Android SDK callback implementations in Kotlin. UTS can call ordinary
 * Kotlin functions, but cannot construct Java interfaces or abstract callback
 * classes directly.
 */
object ShiyaImageAnalysisNative {
  fun initializeTextModeration(
    context: Context,
    onSuccess: () -> Unit,
    onFailed: (Int, String) -> Unit,
  ) {
    CmsLocalFrame.getInstance().init(context, object : IInitializeListener {
      override fun onInitSuccess() {
        onSuccess()
      }

      override fun onInitFailed(code: Int, message: String) {
        onFailed(code, message)
      }
    })
  }

  fun moderateText(
    text: String,
    timeout: Int,
    onResult: (Int, String) -> Unit,
  ) {
    CmsLocalFrame.getInstance().TextModeration(
      text,
      object : CommApiCallBack<ResponseResult>() {
        override fun onCallBack(responseResult: ResponseResult?) {
          if (responseResult == null) {
            onResult(110007, "")
            return
          }
          onResult(responseResult.code, responseResult.data ?: "")
        }
      },
      timeout,
    )
  }

  fun generate(
    manager: LlmManager,
    prompt: String,
    onToken: (String) -> Unit,
    onComplete: () -> Unit,
    onError: (Int, String) -> Unit,
  ) {
    manager.generate(prompt, object : TokenCallback {
      override fun onToken(token: String) {
        onToken(token)
      }

      override fun onComplete() {
        onComplete()
      }

      override fun onError(code: Int, message: String) {
        onError(code, message)
      }
    })
  }
}
