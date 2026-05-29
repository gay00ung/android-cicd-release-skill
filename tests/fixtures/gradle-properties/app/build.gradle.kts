plugins {
    id("com.android.application")
}

android {
    namespace = "com.example.properties"

    defaultConfig {
        applicationId = "com.example.properties"
        versionCode = VERSION_CODE.toInt()
        versionName = VERSION_NAME
    }
}
