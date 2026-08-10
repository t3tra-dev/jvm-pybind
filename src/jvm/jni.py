"""JNI関数バインディング"""

from __future__ import annotations

import ctypes
import platform
from ctypes import (
    POINTER,
    Union,
    c_bool,
    c_char_p,
    c_double,
    c_float,
    c_int,
    c_int8,
    c_int16,
    c_int32,
    c_int64,
    c_uint16,
    c_void_p,
)
from typing import Any, Optional, cast

from .logger import logger
from .signature import array_component_type, java_type_to_descriptor

# JNI基本型
jboolean = c_bool
jbyte = c_int8
jchar = c_uint16
jshort = c_int16
jint = c_int32
jlong = c_int64
jfloat = c_float
jdouble = c_double
jobject = c_void_p


class jvalue(Union):
    """JNI引数共用体"""

    _fields_ = [
        ("z", jboolean),
        ("b", jbyte),
        ("c", jchar),
        ("s", jshort),
        ("i", jint),
        ("j", jlong),
        ("f", jfloat),
        ("d", jdouble),
        ("l", jobject),
    ]

    # ARM64 macOS用アライメント
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        _pack_ = 8
        _align_ = 8
    else:
        _pack_ = 8


def _convert_args_to_jvalue_array(args: tuple[Any, ...]) -> tuple[Any, int]:
    """Python引数をjvalue配列に変換"""
    if not args:
        return None, 0

    jvalue_array = (jvalue * len(args))()

    # ARM64 macOSでのアライメント調整
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        array_addr = ctypes.addressof(jvalue_array)
        if array_addr % 8 != 0:
            aligned_array = (jvalue * len(args))()
            aligned_addr = ctypes.addressof(aligned_array)
            if aligned_addr % 8 == 0:
                jvalue_array = aligned_array

    for i, arg in enumerate(args):
        ctypes.memset(ctypes.byref(jvalue_array[i]), 0, ctypes.sizeof(jvalue))

        if isinstance(arg, bool):
            jvalue_array[i].z = jboolean(arg)
        elif isinstance(arg, int):
            if -(2**31) <= arg <= 2**31 - 1:
                jvalue_array[i].i = jint(arg)
            else:
                jvalue_array[i].j = jlong(arg)
        elif isinstance(arg, float):
            jvalue_array[i].d = jdouble(arg)
        else:
            if isinstance(arg, int) or hasattr(arg, "value"):
                jvalue_array[i].l = arg  # noqa: E741
            else:
                jvalue_array[i].l = jobject(arg) if arg is not None else jobject(0)  # noqa: E741

    return jvalue_array, len(args)


class JNIFunctionIndices:
    """JNI関数インデックス定数"""

    RESERVED_0 = 0
    RESERVED_1 = 1
    RESERVED_2 = 2
    RESERVED_3 = 3
    GetVersion = 4
    DefineClass = 5
    FindClass = 6
    FromReflectedMethod = 7
    FromReflectedField = 8
    ToReflectedMethod = 9
    GetSuperclass = 10
    IsAssignableFrom = 11
    ToReflectedField = 12
    Throw = 13
    ThrowNew = 14
    ExceptionOccurred = 15
    ExceptionDescribe = 16
    ExceptionClear = 17
    FatalError = 18
    PushLocalFrame = 19
    PopLocalFrame = 20
    NewGlobalRef = 21
    DeleteGlobalRef = 22
    DeleteLocalRef = 23
    IsSameObject = 24
    NewLocalRef = 25
    EnsureLocalCapacity = 26
    AllocObject = 27
    NewObject = 28
    NewObjectV = 29
    NewObjectA = 30
    GetObjectClass = 31
    IsInstanceOf = 32
    GetMethodID = 33
    CallObjectMethod = 34
    CallObjectMethodV = 35
    CallObjectMethodA = 36
    CallBooleanMethod = 37
    CallBooleanMethodV = 38
    CallBooleanMethodA = 39
    CallByteMethod = 40
    CallByteMethodV = 41
    CallByteMethodA = 42
    CallCharMethod = 43
    CallCharMethodV = 44
    CallCharMethodA = 45
    CallShortMethod = 46
    CallShortMethodV = 47
    CallShortMethodA = 48
    CallIntMethod = 49
    CallIntMethodV = 50
    CallIntMethodA = 51
    CallLongMethod = 52
    CallLongMethodV = 53
    CallLongMethodA = 54
    CallFloatMethod = 55
    CallFloatMethodV = 56
    CallFloatMethodA = 57
    CallDoubleMethod = 58
    CallDoubleMethodV = 59
    CallDoubleMethodA = 60
    CallVoidMethod = 61
    CallVoidMethodV = 62
    CallVoidMethodA = 63
    CallNonvirtualObjectMethod = 64
    CallNonvirtualObjectMethodV = 65
    CallNonvirtualObjectMethodA = 66
    CallNonvirtualBooleanMethod = 67
    CallNonvirtualBooleanMethodV = 68
    CallNonvirtualBooleanMethodA = 69
    CallNonvirtualByteMethod = 70
    CallNonvirtualByteMethodV = 71
    CallNonvirtualByteMethodA = 72
    CallNonvirtualCharMethod = 73
    CallNonvirtualCharMethodV = 74
    CallNonvirtualCharMethodA = 75
    CallNonvirtualShortMethod = 76
    CallNonvirtualShortMethodV = 77
    CallNonvirtualShortMethodA = 78
    CallNonvirtualIntMethod = 79
    CallNonvirtualIntMethodV = 80
    CallNonvirtualIntMethodA = 81
    CallNonvirtualLongMethod = 82
    CallNonvirtualLongMethodV = 83
    CallNonvirtualLongMethodA = 84
    CallNonvirtualFloatMethod = 85
    CallNonvirtualFloatMethodV = 86
    CallNonvirtualFloatMethodA = 87
    CallNonvirtualDoubleMethod = 88
    CallNonvirtualDoubleMethodV = 89
    CallNonvirtualDoubleMethodA = 90
    CallNonvirtualVoidMethod = 91
    CallNonvirtualVoidMethodV = 92
    CallNonvirtualVoidMethodA = 93
    GetFieldID = 94
    GetObjectField = 95
    GetBooleanField = 96
    GetByteField = 97
    GetCharField = 98
    GetShortField = 99
    GetIntField = 100
    GetLongField = 101
    GetFloatField = 102
    GetDoubleField = 103
    SetObjectField = 104
    SetBooleanField = 105
    SetByteField = 106
    SetCharField = 107
    SetShortField = 108
    SetIntField = 109
    SetLongField = 110
    SetFloatField = 111
    SetDoubleField = 112
    GetStaticMethodID = 113
    CallStaticObjectMethod = 114
    CallStaticObjectMethodV = 115
    CallStaticObjectMethodA = 116
    CallStaticBooleanMethod = 117
    CallStaticBooleanMethodV = 118
    CallStaticBooleanMethodA = 119
    CallStaticByteMethod = 120
    CallStaticByteMethodV = 121
    CallStaticByteMethodA = 122
    CallStaticCharMethod = 123
    CallStaticCharMethodV = 124
    CallStaticCharMethodA = 125
    CallStaticShortMethod = 126
    CallStaticShortMethodV = 127
    CallStaticShortMethodA = 128
    CallStaticIntMethod = 129
    CallStaticIntMethodV = 130
    CallStaticIntMethodA = 131
    CallStaticLongMethod = 132
    CallStaticLongMethodV = 133
    CallStaticLongMethodA = 134
    CallStaticFloatMethod = 135
    CallStaticFloatMethodV = 136
    CallStaticFloatMethodA = 137
    CallStaticDoubleMethod = 138
    CallStaticDoubleMethodV = 139
    CallStaticDoubleMethodA = 140
    CallStaticVoidMethod = 141
    CallStaticVoidMethodV = 142
    CallStaticVoidMethodA = 143
    GetStaticFieldID = 144
    GetStaticObjectField = 145
    GetStaticBooleanField = 146
    GetStaticByteField = 147
    GetStaticCharField = 148
    GetStaticShortField = 149
    GetStaticIntField = 150
    GetStaticLongField = 151
    GetStaticFloatField = 152
    GetStaticDoubleField = 153
    SetStaticObjectField = 154
    SetStaticBooleanField = 155
    SetStaticByteField = 156
    SetStaticCharField = 157
    SetStaticShortField = 158
    SetStaticIntField = 159
    SetStaticLongField = 160
    SetStaticFloatField = 161
    SetStaticDoubleField = 162
    NewString = 163
    GetStringLength = 164
    GetStringChars = 165
    ReleaseStringChars = 166
    NewStringUTF = 167
    GetStringUTFLength = 168
    GetStringUTFChars = 169
    ReleaseStringUTFChars = 170
    GetArrayLength = 171
    NewObjectArray = 172
    GetObjectArrayElement = 173
    SetObjectArrayElement = 174
    NewBooleanArray = 175
    NewByteArray = 176
    NewCharArray = 177
    NewShortArray = 178
    NewIntArray = 179
    NewLongArray = 180
    NewFloatArray = 181
    NewDoubleArray = 182
    GetBooleanArrayElements = 183
    GetByteArrayElements = 184
    GetCharArrayElements = 185
    GetShortArrayElements = 186
    GetIntArrayElements = 187
    GetLongArrayElements = 188
    GetFloatArrayElements = 189
    GetDoubleArrayElements = 190
    ReleaseBooleanArrayElements = 191
    ReleaseByteArrayElements = 192
    ReleaseCharArrayElements = 193
    ReleaseShortArrayElements = 194
    ReleaseIntArrayElements = 195
    ReleaseLongArrayElements = 196
    ReleaseFloatArrayElements = 197
    ReleaseDoubleArrayElements = 198
    GetBooleanArrayRegion = 199
    GetByteArrayRegion = 200
    GetCharArrayRegion = 201
    GetShortArrayRegion = 202
    GetIntArrayRegion = 203
    GetLongArrayRegion = 204
    GetFloatArrayRegion = 205
    GetDoubleArrayRegion = 206
    SetBooleanArrayRegion = 207
    SetByteArrayRegion = 208
    SetCharArrayRegion = 209
    SetShortArrayRegion = 210
    SetIntArrayRegion = 211
    SetLongArrayRegion = 212
    SetFloatArrayRegion = 213
    SetDoubleArrayRegion = 214
    RegisterNatives = 215
    UnregisterNatives = 216
    MonitorEnter = 217
    MonitorExit = 218
    GetJavaVM = 219
    GetStringRegion = 220
    GetStringUTFRegion = 221
    GetPrimitiveArrayCritical = 222
    ReleasePrimitiveArrayCritical = 223
    GetStringCritical = 224
    ReleaseStringCritical = 225
    NewWeakGlobalRef = 226
    DeleteWeakGlobalRef = 227
    ExceptionCheck = 228
    NewDirectByteBuffer = 229
    GetDirectBufferAddress = 230
    GetDirectBufferCapacity = 231
    GetObjectRefType = 232


class JNIPrototypes:
    """JNI関数プロトタイプ"""

    JNIEnv = POINTER(c_void_p)
    JavaVM = POINTER(c_void_p)
    jobject = c_void_p
    jclass = c_void_p
    jstring = c_void_p
    jarray = c_void_p
    jmethodID = c_void_p
    jfieldID = c_void_p
    jthrowable = c_void_p
    jsize = c_int
    jint = jint
    jboolean = c_bool
    jbyte = jbyte
    jchar = jchar
    jshort = jshort
    jlong = jlong
    jfloat = jfloat
    jdouble = jdouble

    GetVersion = ctypes.CFUNCTYPE(jint, JNIEnv)
    DefineClass = ctypes.CFUNCTYPE(
        jclass, JNIEnv, c_char_p, jobject, POINTER(ctypes.c_byte), jsize
    )
    FindClass = ctypes.CFUNCTYPE(jclass, JNIEnv, c_char_p)
    GetSuperclass = ctypes.CFUNCTYPE(jclass, JNIEnv, jclass)
    IsAssignableFrom = ctypes.CFUNCTYPE(jboolean, JNIEnv, jclass, jclass)
    AllocObject = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass)
    NewObject = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jmethodID)
    NewObjectV = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jmethodID, ctypes.c_char_p)
    NewObjectA = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jmethodID, POINTER(jvalue))
    GetObjectClass = ctypes.CFUNCTYPE(jclass, JNIEnv, jobject)
    IsInstanceOf = ctypes.CFUNCTYPE(jboolean, JNIEnv, jobject, jclass)
    IsSameObject = ctypes.CFUNCTYPE(jboolean, JNIEnv, jobject, jobject)
    GetMethodID = ctypes.CFUNCTYPE(jmethodID, JNIEnv, jclass, c_char_p, c_char_p)
    CallObjectMethod = ctypes.CFUNCTYPE(jobject, JNIEnv, jobject, jmethodID)
    CallObjectMethodV = ctypes.CFUNCTYPE(
        jobject, JNIEnv, jobject, jmethodID, ctypes.c_char_p
    )
    CallObjectMethodA = ctypes.CFUNCTYPE(
        jobject, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallBooleanMethod = ctypes.CFUNCTYPE(jboolean, JNIEnv, jobject, jmethodID)
    CallBooleanMethodA = ctypes.CFUNCTYPE(
        jboolean, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallByteMethodA = ctypes.CFUNCTYPE(
        jbyte, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallCharMethodA = ctypes.CFUNCTYPE(
        jchar, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallShortMethodA = ctypes.CFUNCTYPE(
        jshort, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallIntMethod = ctypes.CFUNCTYPE(jint, JNIEnv, jobject, jmethodID)
    CallIntMethodA = ctypes.CFUNCTYPE(jint, JNIEnv, jobject, jmethodID, POINTER(jvalue))
    CallLongMethodA = ctypes.CFUNCTYPE(
        jlong, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallFloatMethodA = ctypes.CFUNCTYPE(
        jfloat, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallDoubleMethodA = ctypes.CFUNCTYPE(
        jdouble, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    CallVoidMethod = ctypes.CFUNCTYPE(None, JNIEnv, jobject, jmethodID)
    CallVoidMethodA = ctypes.CFUNCTYPE(
        None, JNIEnv, jobject, jmethodID, POINTER(jvalue)
    )
    GetStaticMethodID = ctypes.CFUNCTYPE(jmethodID, JNIEnv, jclass, c_char_p, c_char_p)
    CallStaticObjectMethod = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jmethodID)
    CallStaticObjectMethodV = ctypes.CFUNCTYPE(
        jobject, JNIEnv, jclass, jmethodID, ctypes.c_char_p
    )
    CallStaticObjectMethodA = ctypes.CFUNCTYPE(
        jobject, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticBooleanMethodA = ctypes.CFUNCTYPE(
        jboolean, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticByteMethodA = ctypes.CFUNCTYPE(
        jbyte, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticCharMethodA = ctypes.CFUNCTYPE(
        jchar, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticShortMethodA = ctypes.CFUNCTYPE(
        jshort, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticIntMethodA = ctypes.CFUNCTYPE(
        jint, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticLongMethodA = ctypes.CFUNCTYPE(
        jlong, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticFloatMethodA = ctypes.CFUNCTYPE(
        jfloat, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticDoubleMethodA = ctypes.CFUNCTYPE(
        jdouble, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    CallStaticVoidMethod = ctypes.CFUNCTYPE(None, JNIEnv, jclass, jmethodID)
    CallStaticVoidMethodV = ctypes.CFUNCTYPE(
        None, JNIEnv, jclass, jmethodID, ctypes.c_char_p
    )
    CallStaticVoidMethodA = ctypes.CFUNCTYPE(
        None, JNIEnv, jclass, jmethodID, POINTER(jvalue)
    )
    GetFieldID = ctypes.CFUNCTYPE(jfieldID, JNIEnv, jclass, c_char_p, c_char_p)
    GetObjectField = ctypes.CFUNCTYPE(jobject, JNIEnv, jobject, jfieldID)
    GetBooleanField = ctypes.CFUNCTYPE(jboolean, JNIEnv, jobject, jfieldID)
    GetByteField = ctypes.CFUNCTYPE(jbyte, JNIEnv, jobject, jfieldID)
    GetCharField = ctypes.CFUNCTYPE(jchar, JNIEnv, jobject, jfieldID)
    GetShortField = ctypes.CFUNCTYPE(jshort, JNIEnv, jobject, jfieldID)
    GetIntField = ctypes.CFUNCTYPE(jint, JNIEnv, jobject, jfieldID)
    GetLongField = ctypes.CFUNCTYPE(jlong, JNIEnv, jobject, jfieldID)
    GetFloatField = ctypes.CFUNCTYPE(jfloat, JNIEnv, jobject, jfieldID)
    GetDoubleField = ctypes.CFUNCTYPE(jdouble, JNIEnv, jobject, jfieldID)
    SetObjectField = ctypes.CFUNCTYPE(None, JNIEnv, jobject, jfieldID, jobject)
    GetStaticFieldID = ctypes.CFUNCTYPE(jfieldID, JNIEnv, jclass, c_char_p, c_char_p)
    GetStaticObjectField = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jfieldID)
    GetStaticBooleanField = ctypes.CFUNCTYPE(jboolean, JNIEnv, jclass, jfieldID)
    GetStaticByteField = ctypes.CFUNCTYPE(jbyte, JNIEnv, jclass, jfieldID)
    GetStaticCharField = ctypes.CFUNCTYPE(jchar, JNIEnv, jclass, jfieldID)
    GetStaticShortField = ctypes.CFUNCTYPE(jshort, JNIEnv, jclass, jfieldID)
    GetStaticIntField = ctypes.CFUNCTYPE(jint, JNIEnv, jclass, jfieldID)
    GetStaticLongField = ctypes.CFUNCTYPE(jlong, JNIEnv, jclass, jfieldID)
    GetStaticFloatField = ctypes.CFUNCTYPE(jfloat, JNIEnv, jclass, jfieldID)
    GetStaticDoubleField = ctypes.CFUNCTYPE(jdouble, JNIEnv, jclass, jfieldID)
    SetStaticObjectField = ctypes.CFUNCTYPE(None, JNIEnv, jclass, jfieldID, jobject)
    NewString = ctypes.CFUNCTYPE(jstring, JNIEnv, POINTER(ctypes.c_uint16), jsize)
    GetStringLength = ctypes.CFUNCTYPE(jsize, JNIEnv, jstring)
    GetStringChars = ctypes.CFUNCTYPE(
        POINTER(ctypes.c_uint16), JNIEnv, jstring, POINTER(jboolean)
    )
    ReleaseStringChars = ctypes.CFUNCTYPE(
        None, JNIEnv, jstring, POINTER(ctypes.c_uint16)
    )
    NewStringUTF = ctypes.CFUNCTYPE(jstring, JNIEnv, c_char_p)
    GetStringUTFLength = ctypes.CFUNCTYPE(jsize, JNIEnv, jstring)
    GetStringUTFChars = ctypes.CFUNCTYPE(c_char_p, JNIEnv, jstring, POINTER(jboolean))
    ReleaseStringUTFChars = ctypes.CFUNCTYPE(None, JNIEnv, jstring, c_char_p)
    GetArrayLength = ctypes.CFUNCTYPE(jsize, JNIEnv, jarray)
    NewObjectArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize, jclass, jobject)
    GetObjectArrayElement = ctypes.CFUNCTYPE(jobject, JNIEnv, jarray, jsize)
    SetObjectArrayElement = ctypes.CFUNCTYPE(None, JNIEnv, jarray, jsize, jobject)
    NewBooleanArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewByteArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewCharArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewShortArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewIntArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewLongArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewFloatArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    NewDoubleArray = ctypes.CFUNCTYPE(jarray, JNIEnv, jsize)
    GetBooleanArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jboolean)
    )
    GetByteArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jbyte)
    )
    GetCharArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jchar)
    )
    GetShortArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jshort)
    )
    GetIntArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jint)
    )
    GetLongArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jlong)
    )
    GetFloatArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jfloat)
    )
    GetDoubleArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jdouble)
    )
    SetBooleanArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jboolean)
    )
    SetByteArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jbyte)
    )
    SetCharArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jchar)
    )
    SetShortArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jshort)
    )
    SetIntArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jint)
    )
    SetLongArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jlong)
    )
    SetFloatArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jfloat)
    )
    SetDoubleArrayRegion = ctypes.CFUNCTYPE(
        None, JNIEnv, jarray, jsize, jsize, POINTER(jdouble)
    )
    Throw = ctypes.CFUNCTYPE(jint, JNIEnv, jthrowable)
    ThrowNew = ctypes.CFUNCTYPE(jint, JNIEnv, jclass, c_char_p)
    ExceptionOccurred = ctypes.CFUNCTYPE(jthrowable, JNIEnv)
    ExceptionDescribe = ctypes.CFUNCTYPE(None, JNIEnv)
    ExceptionClear = ctypes.CFUNCTYPE(None, JNIEnv)
    FatalError = ctypes.CFUNCTYPE(None, JNIEnv, c_char_p)
    ExceptionCheck = ctypes.CFUNCTYPE(jboolean, JNIEnv)
    NewGlobalRef = ctypes.CFUNCTYPE(jobject, JNIEnv, jobject)
    DeleteGlobalRef = ctypes.CFUNCTYPE(None, JNIEnv, jobject)
    DeleteLocalRef = ctypes.CFUNCTYPE(None, JNIEnv, jobject)
    NewLocalRef = ctypes.CFUNCTYPE(jobject, JNIEnv, jobject)
    EnsureLocalCapacity = ctypes.CFUNCTYPE(jint, JNIEnv, jint)
    PushLocalFrame = ctypes.CFUNCTYPE(jint, JNIEnv, jint)
    PopLocalFrame = ctypes.CFUNCTYPE(jobject, JNIEnv, jobject)
    NewWeakGlobalRef = ctypes.CFUNCTYPE(c_void_p, JNIEnv, jobject)
    DeleteWeakGlobalRef = ctypes.CFUNCTYPE(None, JNIEnv, c_void_p)
    MonitorEnter = ctypes.CFUNCTYPE(jint, JNIEnv, jobject)
    MonitorExit = ctypes.CFUNCTYPE(jint, JNIEnv, jobject)
    GetJavaVM = ctypes.CFUNCTYPE(jint, JNIEnv, POINTER(JavaVM))
    FromReflectedMethod = ctypes.CFUNCTYPE(jmethodID, JNIEnv, jobject)
    FromReflectedField = ctypes.CFUNCTYPE(jfieldID, JNIEnv, jobject)
    ToReflectedMethod = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jmethodID, jboolean)
    ToReflectedField = ctypes.CFUNCTYPE(jobject, JNIEnv, jclass, jfieldID, jboolean)


_JAVA_TYPE_DESCRIPTORS = {
    "boolean": "Z",
    "byte": "B",
    "char": "C",
    "short": "S",
    "int": "I",
    "long": "J",
    "float": "F",
    "double": "D",
}
_PRIMITIVE_JAVA_TYPES = frozenset(_JAVA_TYPE_DESCRIPTORS)

_INTEGRAL_JAVA_RANGES = {
    "byte": (-(2**7), 2**7 - 1),
    "short": (-(2**15), 2**15 - 1),
    "int": (-(2**31), 2**31 - 1),
    "long": (-(2**63), 2**63 - 1),
}

_BOXED_INTEGRAL_JAVA_TYPES = {
    "java.lang.Byte": "byte",
    "java.lang.Short": "short",
    "java.lang.Integer": "int",
    "java.lang.Long": "long",
}

_TYPED_INSTANCE_CALLS = {
    "object": (
        JNIFunctionIndices.CallObjectMethodA,
        JNIPrototypes.CallObjectMethodA,
    ),
    "boolean": (
        JNIFunctionIndices.CallBooleanMethodA,
        JNIPrototypes.CallBooleanMethodA,
    ),
    "byte": (JNIFunctionIndices.CallByteMethodA, JNIPrototypes.CallByteMethodA),
    "char": (JNIFunctionIndices.CallCharMethodA, JNIPrototypes.CallCharMethodA),
    "short": (JNIFunctionIndices.CallShortMethodA, JNIPrototypes.CallShortMethodA),
    "int": (JNIFunctionIndices.CallIntMethodA, JNIPrototypes.CallIntMethodA),
    "long": (JNIFunctionIndices.CallLongMethodA, JNIPrototypes.CallLongMethodA),
    "float": (JNIFunctionIndices.CallFloatMethodA, JNIPrototypes.CallFloatMethodA),
    "double": (
        JNIFunctionIndices.CallDoubleMethodA,
        JNIPrototypes.CallDoubleMethodA,
    ),
    "void": (JNIFunctionIndices.CallVoidMethodA, JNIPrototypes.CallVoidMethodA),
}

_TYPED_STATIC_CALLS = {
    "object": (
        JNIFunctionIndices.CallStaticObjectMethodA,
        JNIPrototypes.CallStaticObjectMethodA,
    ),
    "boolean": (
        JNIFunctionIndices.CallStaticBooleanMethodA,
        JNIPrototypes.CallStaticBooleanMethodA,
    ),
    "byte": (
        JNIFunctionIndices.CallStaticByteMethodA,
        JNIPrototypes.CallStaticByteMethodA,
    ),
    "char": (
        JNIFunctionIndices.CallStaticCharMethodA,
        JNIPrototypes.CallStaticCharMethodA,
    ),
    "short": (
        JNIFunctionIndices.CallStaticShortMethodA,
        JNIPrototypes.CallStaticShortMethodA,
    ),
    "int": (
        JNIFunctionIndices.CallStaticIntMethodA,
        JNIPrototypes.CallStaticIntMethodA,
    ),
    "long": (
        JNIFunctionIndices.CallStaticLongMethodA,
        JNIPrototypes.CallStaticLongMethodA,
    ),
    "float": (
        JNIFunctionIndices.CallStaticFloatMethodA,
        JNIPrototypes.CallStaticFloatMethodA,
    ),
    "double": (
        JNIFunctionIndices.CallStaticDoubleMethodA,
        JNIPrototypes.CallStaticDoubleMethodA,
    ),
    "void": (
        JNIFunctionIndices.CallStaticVoidMethodA,
        JNIPrototypes.CallStaticVoidMethodA,
    ),
}

_TYPED_INSTANCE_FIELD_GETTERS = {
    "object": (JNIFunctionIndices.GetObjectField, JNIPrototypes.GetObjectField),
    "boolean": (JNIFunctionIndices.GetBooleanField, JNIPrototypes.GetBooleanField),
    "byte": (JNIFunctionIndices.GetByteField, JNIPrototypes.GetByteField),
    "char": (JNIFunctionIndices.GetCharField, JNIPrototypes.GetCharField),
    "short": (JNIFunctionIndices.GetShortField, JNIPrototypes.GetShortField),
    "int": (JNIFunctionIndices.GetIntField, JNIPrototypes.GetIntField),
    "long": (JNIFunctionIndices.GetLongField, JNIPrototypes.GetLongField),
    "float": (JNIFunctionIndices.GetFloatField, JNIPrototypes.GetFloatField),
    "double": (JNIFunctionIndices.GetDoubleField, JNIPrototypes.GetDoubleField),
}

_TYPED_STATIC_FIELD_GETTERS = {
    "object": (
        JNIFunctionIndices.GetStaticObjectField,
        JNIPrototypes.GetStaticObjectField,
    ),
    "boolean": (
        JNIFunctionIndices.GetStaticBooleanField,
        JNIPrototypes.GetStaticBooleanField,
    ),
    "byte": (
        JNIFunctionIndices.GetStaticByteField,
        JNIPrototypes.GetStaticByteField,
    ),
    "char": (
        JNIFunctionIndices.GetStaticCharField,
        JNIPrototypes.GetStaticCharField,
    ),
    "short": (
        JNIFunctionIndices.GetStaticShortField,
        JNIPrototypes.GetStaticShortField,
    ),
    "int": (
        JNIFunctionIndices.GetStaticIntField,
        JNIPrototypes.GetStaticIntField,
    ),
    "long": (
        JNIFunctionIndices.GetStaticLongField,
        JNIPrototypes.GetStaticLongField,
    ),
    "float": (
        JNIFunctionIndices.GetStaticFloatField,
        JNIPrototypes.GetStaticFloatField,
    ),
    "double": (
        JNIFunctionIndices.GetStaticDoubleField,
        JNIPrototypes.GetStaticDoubleField,
    ),
}

_PRIMITIVE_ARRAY_OPERATIONS: dict[str, tuple[Any, int, Any, int, Any, int, Any]] = {
    "boolean": (
        jboolean,
        JNIFunctionIndices.NewBooleanArray,
        JNIPrototypes.NewBooleanArray,
        JNIFunctionIndices.GetBooleanArrayRegion,
        JNIPrototypes.GetBooleanArrayRegion,
        JNIFunctionIndices.SetBooleanArrayRegion,
        JNIPrototypes.SetBooleanArrayRegion,
    ),
    "byte": (
        jbyte,
        JNIFunctionIndices.NewByteArray,
        JNIPrototypes.NewByteArray,
        JNIFunctionIndices.GetByteArrayRegion,
        JNIPrototypes.GetByteArrayRegion,
        JNIFunctionIndices.SetByteArrayRegion,
        JNIPrototypes.SetByteArrayRegion,
    ),
    "char": (
        jchar,
        JNIFunctionIndices.NewCharArray,
        JNIPrototypes.NewCharArray,
        JNIFunctionIndices.GetCharArrayRegion,
        JNIPrototypes.GetCharArrayRegion,
        JNIFunctionIndices.SetCharArrayRegion,
        JNIPrototypes.SetCharArrayRegion,
    ),
    "short": (
        jshort,
        JNIFunctionIndices.NewShortArray,
        JNIPrototypes.NewShortArray,
        JNIFunctionIndices.GetShortArrayRegion,
        JNIPrototypes.GetShortArrayRegion,
        JNIFunctionIndices.SetShortArrayRegion,
        JNIPrototypes.SetShortArrayRegion,
    ),
    "int": (
        jint,
        JNIFunctionIndices.NewIntArray,
        JNIPrototypes.NewIntArray,
        JNIFunctionIndices.GetIntArrayRegion,
        JNIPrototypes.GetIntArrayRegion,
        JNIFunctionIndices.SetIntArrayRegion,
        JNIPrototypes.SetIntArrayRegion,
    ),
    "long": (
        jlong,
        JNIFunctionIndices.NewLongArray,
        JNIPrototypes.NewLongArray,
        JNIFunctionIndices.GetLongArrayRegion,
        JNIPrototypes.GetLongArrayRegion,
        JNIFunctionIndices.SetLongArrayRegion,
        JNIPrototypes.SetLongArrayRegion,
    ),
    "float": (
        jfloat,
        JNIFunctionIndices.NewFloatArray,
        JNIPrototypes.NewFloatArray,
        JNIFunctionIndices.GetFloatArrayRegion,
        JNIPrototypes.GetFloatArrayRegion,
        JNIFunctionIndices.SetFloatArrayRegion,
        JNIPrototypes.SetFloatArrayRegion,
    ),
    "double": (
        jdouble,
        JNIFunctionIndices.NewDoubleArray,
        JNIPrototypes.NewDoubleArray,
        JNIFunctionIndices.GetDoubleArrayRegion,
        JNIPrototypes.GetDoubleArrayRegion,
        JNIFunctionIndices.SetDoubleArrayRegion,
        JNIPrototypes.SetDoubleArrayRegion,
    ),
}


class JNIHelper:
    """JNI関数呼び出しヘルパー"""

    def __init__(self, env: Any) -> None:
        self.env = env
        self._function_table = self._get_function_table()

    def _check_exception(self) -> None:
        """例外チェックとクリア"""
        if self.ExceptionCheck():
            self.ExceptionDescribe()
            self.ExceptionClear()
            raise RuntimeError("JNI exception occurred")

    def _get_function_table(self) -> Any:
        """JNI関数テーブル取得"""
        env_ptr = ctypes.cast(self.env, POINTER(c_void_p))
        function_table_ptr = ctypes.cast(env_ptr.contents, POINTER(c_void_p))
        return function_table_ptr

    def _get_function(self, index: int, prototype: Any) -> Any:
        """JNI関数取得"""
        return prototype(self._function_table[index])

    def GetVersion(self) -> int:
        func = self._get_function(
            JNIFunctionIndices.GetVersion, JNIPrototypes.GetVersion
        )
        return cast(int, func(self.env))

    def FindClass(self, name: str) -> Optional[Any]:
        func = self._get_function(JNIFunctionIndices.FindClass, JNIPrototypes.FindClass)
        result = func(self.env, name.encode("utf-8"))
        self._check_exception()
        return result

    def GetSuperclass(self, clazz: Any) -> Optional[Any]:
        func = self._get_function(
            JNIFunctionIndices.GetSuperclass, JNIPrototypes.GetSuperclass
        )
        return func(self.env, clazz)

    def IsAssignableFrom(self, clazz1: Any, clazz2: Any) -> bool:
        func = self._get_function(
            JNIFunctionIndices.IsAssignableFrom, JNIPrototypes.IsAssignableFrom
        )
        return bool(func(self.env, clazz1, clazz2))

    def AllocObject(self, clazz: Any) -> Optional[Any]:
        func = self._get_function(
            JNIFunctionIndices.AllocObject, JNIPrototypes.AllocObject
        )
        return func(self.env, clazz)

    def NewObject(self, clazz: Any, method_id: Any, *args: Any) -> Optional[Any]:
        func = self._get_function(JNIFunctionIndices.NewObject, JNIPrototypes.NewObject)
        return func(self.env, clazz, method_id, *args)

    def NewTypedObject(
        self,
        clazz: Any,
        method_id: Any,
        parameter_types: list[str],
        *args: Any,
    ) -> Optional[Any]:
        """Construct an object using reflected constructor parameter types."""
        if len(parameter_types) != len(args):
            raise TypeError(
                f"Expected {len(parameter_types)} constructor arguments, got {len(args)}"
            )
        if not clazz or not method_id:
            raise ValueError("clazz and method_id must not be NULL")

        frame_capacity = max(16, len(args) * 3 + 4)
        if self.PushLocalFrame(frame_capacity) != 0:
            raise RuntimeError("Failed to push local frame")

        result: Any = None
        try:
            jvalue_array = self._convert_typed_args_to_jvalue_array(
                args, parameter_types
            )
            args_ptr = (
                ctypes.cast(jvalue_array, POINTER(jvalue)) if jvalue_array else None
            )
            func = self._get_function(
                JNIFunctionIndices.NewObjectA, JNIPrototypes.NewObjectA
            )
            result = func(self.env, clazz, method_id, args_ptr)
            self._check_exception()
        finally:
            result = self.PopLocalFrame(result)

        return result

    def GetObjectClass(self, obj: Any) -> Optional[Any]:
        if not obj:
            raise ValueError("obj must not be NULL")
        func = self._get_function(
            JNIFunctionIndices.GetObjectClass, JNIPrototypes.GetObjectClass
        )
        result = func(self.env, obj)
        self._check_exception()
        return result

    def IsInstanceOf(self, obj: Any, clazz: Any) -> bool:
        func = self._get_function(
            JNIFunctionIndices.IsInstanceOf, JNIPrototypes.IsInstanceOf
        )
        return bool(func(self.env, obj, clazz))

    def IsSameObject(self, obj1: Any, obj2: Any) -> bool:
        func = self._get_function(
            JNIFunctionIndices.IsSameObject, JNIPrototypes.IsSameObject
        )
        return bool(func(self.env, obj1, obj2))

    # Method Operations
    def GetMethodID(self, clazz: Any, name: str, signature: str) -> Optional[Any]:
        """Get method ID"""
        if not clazz:
            raise ValueError("clazz must not be NULL")
        func = self._get_function(
            JNIFunctionIndices.GetMethodID, JNIPrototypes.GetMethodID
        )
        result = func(self.env, clazz, name.encode("utf-8"), signature.encode("utf-8"))
        self._check_exception()
        return result

    def CallObjectMethodA(self, obj: Any, method_id: Any, args: Any) -> Optional[Any]:
        """Call object method with jvalue argument array"""
        func = self._get_function(
            JNIFunctionIndices.CallObjectMethodA, JNIPrototypes.CallObjectMethodA
        )
        # Pass args as a pointer to the first element for JNI compatibility
        args_ptr = ctypes.cast(args, POINTER(jvalue)) if args else None
        result = func(self.env, obj, method_id, args_ptr)
        self._check_exception()
        return result

    def CallObjectMethod(self, obj: Any, method_id: Any, *args: Any) -> Optional[Any]:
        """Call object method - uses jvalue array for safe argument passing"""
        if not args:
            # No arguments - use direct call
            func = self._get_function(
                JNIFunctionIndices.CallObjectMethod, JNIPrototypes.CallObjectMethod
            )
            result = func(self.env, obj, method_id)
            self._check_exception()
            return result
        else:
            # With arguments - use array version
            jvalue_array, _ = _convert_args_to_jvalue_array(args)
            return self.CallObjectMethodA(obj, method_id, jvalue_array)

    def CallBooleanMethod(self, obj: Any, method_id: Any, *args: Any) -> bool:
        """Call boolean method"""
        func = self._get_function(
            JNIFunctionIndices.CallBooleanMethod, JNIPrototypes.CallBooleanMethod
        )
        return bool(func(self.env, obj, method_id, *args))

    def CallIntMethod(self, obj: Any, method_id: Any, *args: Any) -> int:
        """Call int method"""
        func = self._get_function(
            JNIFunctionIndices.CallIntMethod, JNIPrototypes.CallIntMethod
        )
        return int(func(self.env, obj, method_id, *args))

    def CallVoidMethod(self, obj: Any, method_id: Any, *args: Any) -> None:
        """Call void method - uses jvalue array for safe argument passing"""
        if not obj:
            raise ValueError("obj must not be NULL")
        if not method_id:
            raise ValueError("method_id must not be NULL")

        if not args:
            # No arguments - use direct call
            func = self._get_function(
                JNIFunctionIndices.CallVoidMethod, JNIPrototypes.CallVoidMethod
            )
            func(self.env, obj, method_id)
        else:
            # With arguments - use array version
            func = self._get_function(
                JNIFunctionIndices.CallVoidMethodA, JNIPrototypes.CallVoidMethodA
            )
            jvalue_array, _ = _convert_args_to_jvalue_array(args)
            args_ptr = (
                ctypes.cast(jvalue_array, POINTER(jvalue)) if jvalue_array else None
            )
            func(self.env, obj, method_id, args_ptr)

        self._check_exception()

    def GetStaticMethodID(self, clazz: Any, name: str, signature: str) -> Optional[Any]:
        """Get static method ID"""
        if not clazz:
            raise ValueError("clazz must not be NULL")
        func = self._get_function(
            JNIFunctionIndices.GetStaticMethodID, JNIPrototypes.GetStaticMethodID
        )
        result = func(self.env, clazz, name.encode("utf-8"), signature.encode("utf-8"))
        self._check_exception()
        return result

    def CallStaticObjectMethodA(
        self, clazz: Any, method_id: Any, args: Any
    ) -> Optional[Any]:
        """Call static object method with jvalue argument array"""
        func = self._get_function(
            JNIFunctionIndices.CallStaticObjectMethodA,
            JNIPrototypes.CallStaticObjectMethodA,
        )

        # Validate and convert arguments
        if args is None:
            args_ptr = None
        else:
            # Verify alignment on ARM64 macOS for safety
            if platform.system() == "Darwin" and platform.machine() == "arm64":
                args_addr = ctypes.addressof(args)
                if args_addr % 8 != 0:
                    logger.error(f"jvalue array misaligned on ARM64: {args_addr:#x}")
                    raise RuntimeError(
                        f"jvalue array misaligned on ARM64: {args_addr:#x} (must be 8-byte aligned)"
                    )

            args_ptr = ctypes.cast(args, POINTER(jvalue))

        result = func(self.env, clazz, method_id, args_ptr)
        self._check_exception()
        return result

    def CallStaticObjectMethod(
        self, clazz: Any, method_id: Any, *args: Any
    ) -> Optional[Any]:
        """Call static object method with proper resource management"""
        frame_capacity = max(10, len(args) * 2)
        if self.PushLocalFrame(frame_capacity) != 0:
            raise RuntimeError("Failed to push local frame")

        result = None
        try:
            jni_args = self._convert_python_args_to_jni(args)

            if not jni_args:
                result = self._call_static_method_no_args(clazz, method_id)
            else:
                result = self._call_static_method_with_args(clazz, method_id, jni_args)

        finally:
            result = self.PopLocalFrame(result)

        return result

    def _convert_python_args_to_jni(self, args: tuple[Any, ...]) -> list[Any]:
        """Convert Python arguments to JNI types"""
        jni_args = []
        for arg in args:
            if isinstance(arg, str):
                jni_string = self.NewStringUTF(arg)
                if jni_string is None:
                    raise RuntimeError(f"Failed to create JNI string for: {arg}")
                jni_args.append(jni_string)
            else:
                jni_args.append(arg)
        return jni_args

    def _call_static_method_no_args(self, clazz: Any, method_id: Any) -> Optional[Any]:
        """Call static method with no arguments"""
        func = self._get_function(
            JNIFunctionIndices.CallStaticObjectMethod,
            JNIPrototypes.CallStaticObjectMethod,
        )
        result = func(self.env, clazz, method_id)
        self._check_exception()
        return result

    def _call_static_method_with_args(
        self, clazz: Any, method_id: Any, jni_args: list[Any]
    ) -> Optional[Any]:
        """Call static method with multiple arguments"""
        jvalue_array, _ = _convert_args_to_jvalue_array(tuple(jni_args))
        return self.CallStaticObjectMethodA(clazz, method_id, jvalue_array)

    def CallStaticVoidMethodA(self, clazz: Any, method_id: Any, args: Any) -> None:
        """Call static void method with jvalue argument array"""
        func = self._get_function(
            JNIFunctionIndices.CallStaticVoidMethodA,
            JNIPrototypes.CallStaticVoidMethodA,
        )

        # Validate and convert arguments
        if args is None:
            args_ptr = None
        else:
            args_ptr = ctypes.cast(args, POINTER(jvalue))

        func(self.env, clazz, method_id, args_ptr)
        self._check_exception()

    def CallTypedMethod(
        self,
        obj: Any,
        method_id: Any,
        return_type: str,
        parameter_types: list[str],
        *args: Any,
    ) -> Any:
        """Call an instance method using its reflected parameter and return types."""
        return self._call_typed_method(
            False,
            obj,
            method_id,
            return_type,
            parameter_types,
            args,
        )

    def CallTypedStaticMethod(
        self,
        clazz: Any,
        method_id: Any,
        return_type: str,
        parameter_types: list[str],
        *args: Any,
    ) -> Any:
        """Call a static method using its reflected parameter and return types."""
        return self._call_typed_method(
            True,
            clazz,
            method_id,
            return_type,
            parameter_types,
            args,
        )

    def _call_typed_method(
        self,
        is_static: bool,
        target: Any,
        method_id: Any,
        return_type: str,
        parameter_types: list[str],
        args: tuple[Any, ...],
    ) -> Any:
        if len(parameter_types) != len(args):
            raise TypeError(
                f"Expected {len(parameter_types)} JNI arguments, got {len(args)}"
            )
        if not target or not method_id:
            raise ValueError("target and method_id must not be NULL")

        frame_capacity = max(16, len(args) * 3 + 4)
        if self.PushLocalFrame(frame_capacity) != 0:
            raise RuntimeError("Failed to push local frame")

        result: Any = None
        retained_result: Any = None
        is_reference_result = (
            return_type not in _PRIMITIVE_JAVA_TYPES and return_type != "void"
        )
        try:
            jvalue_array = self._convert_typed_args_to_jvalue_array(
                args, parameter_types
            )
            args_ptr = (
                ctypes.cast(jvalue_array, POINTER(jvalue)) if jvalue_array else None
            )
            index, prototype = self._typed_call_spec(is_static, return_type)
            func = self._get_function(index, prototype)
            result = func(self.env, target, method_id, args_ptr)
            self._check_exception()
        finally:
            retained_result = self.PopLocalFrame(
                result if is_reference_result else None
            )

        return retained_result if is_reference_result else result

    def _convert_typed_args_to_jvalue_array(
        self, args: tuple[Any, ...], parameter_types: list[str]
    ) -> Any:
        if not args:
            return None

        values = (jvalue * len(args))()
        for index, (argument, parameter_type) in enumerate(zip(args, parameter_types)):
            ctypes.memset(ctypes.byref(values[index]), 0, ctypes.sizeof(jvalue))
            if parameter_type in _PRIMITIVE_JAVA_TYPES:
                self._validate_primitive_argument(argument, parameter_type)
            if parameter_type == "boolean":
                values[index].z = jboolean(argument)
            elif parameter_type == "byte":
                values[index].b = jbyte(argument)
            elif parameter_type == "char":
                char_value = ord(argument) if isinstance(argument, str) else argument
                values[index].c = jchar(char_value)
            elif parameter_type == "short":
                values[index].s = jshort(argument)
            elif parameter_type == "int":
                values[index].i = jint(argument)
            elif parameter_type == "long":
                values[index].j = jlong(argument)
            elif parameter_type == "float":
                values[index].f = jfloat(argument)
            elif parameter_type == "double":
                values[index].d = jdouble(argument)
            else:
                values[index].l = self._prepare_reference_argument(
                    argument, parameter_type
                )
        return values

    @staticmethod
    def _validate_primitive_argument(argument: Any, parameter_type: str) -> None:
        if argument is None:
            raise TypeError(f"None is not valid for primitive {parameter_type}")
        if parameter_type == "boolean":
            if not isinstance(argument, bool):
                raise TypeError("Java boolean arguments require a Python bool")
            return
        if parameter_type in _INTEGRAL_JAVA_RANGES:
            if isinstance(argument, bool) or not isinstance(argument, int):
                raise TypeError(f"Java {parameter_type} arguments require a Python int")
            lower, upper = _INTEGRAL_JAVA_RANGES[parameter_type]
            if not lower <= argument <= upper:
                raise OverflowError(
                    f"{argument} is outside the Java {parameter_type} range"
                )
            return
        if parameter_type == "char":
            if not isinstance(argument, str) or len(argument) != 1:
                raise TypeError("Java char arguments require one UTF-16 code unit")
            if ord(argument) > 0xFFFF:
                raise TypeError("Java char arguments require one UTF-16 code unit")
            return
        if isinstance(argument, bool) or not isinstance(argument, (int, float)):
            raise TypeError(
                f"Java {parameter_type} arguments require a Python int or float"
            )

    def _prepare_reference_argument(self, argument: Any, parameter_type: str) -> Any:
        if argument is None:
            return jobject(0)
        if hasattr(argument, "_jobject"):
            return argument._jobject
        if isinstance(argument, str):
            if parameter_type == "java.lang.Character":
                self._validate_primitive_argument(argument, "char")
                return self._box_primitive("java.lang.Character", "char", argument)
            result = self.NewStringUTF(argument)
            if not result:
                raise RuntimeError("Failed to create Java string argument")
            return result
        if isinstance(argument, bool):
            return self._box_primitive("java.lang.Boolean", "boolean", argument)
        if isinstance(argument, int):
            primitive = _BOXED_INTEGRAL_JAVA_TYPES.get(parameter_type)
            if primitive is None:
                primitive = "int" if -(2**31) <= argument <= 2**31 - 1 else "long"
            self._validate_primitive_argument(argument, primitive)
            wrapper = f"java.lang.{primitive.title()}"
            if primitive == "int":
                wrapper = "java.lang.Integer"
            return self._box_primitive(wrapper, primitive, argument)
        if isinstance(argument, float):
            primitive = "float" if parameter_type == "java.lang.Float" else "double"
            wrapper = f"java.lang.{primitive.title()}"
            return self._box_primitive(wrapper, primitive, argument)
        if isinstance(argument, (list, tuple)):
            return self.NewTypedArray(parameter_type, argument)
        if isinstance(argument, c_void_p):
            return argument
        if hasattr(argument, "value"):
            return argument
        raise TypeError(
            f"Cannot convert {type(argument).__name__} to Java {parameter_type}"
        )

    def _box_primitive(self, wrapper_type: str, primitive_type: str, value: Any) -> Any:
        wrapper_class = self.FindClass(wrapper_type.replace(".", "/"))
        if not wrapper_class:
            raise RuntimeError(f"Could not find {wrapper_type}")
        signature = (
            f"({_JAVA_TYPE_DESCRIPTORS[primitive_type]})"
            f"L{wrapper_type.replace('.', '/')};"
        )
        method_id = self.GetStaticMethodID(wrapper_class, "valueOf", signature)
        if not method_id:
            raise RuntimeError(f"Could not find {wrapper_type}.valueOf")
        return self.CallTypedStaticMethod(
            wrapper_class,
            method_id,
            wrapper_type,
            [primitive_type],
            value,
        )

    @staticmethod
    def _typed_call_spec(is_static: bool, return_type: str) -> tuple[int, Any]:
        kind = (
            return_type
            if return_type in _PRIMITIVE_JAVA_TYPES or return_type == "void"
            else "object"
        )
        try:
            return (
                _TYPED_STATIC_CALLS[kind] if is_static else _TYPED_INSTANCE_CALLS[kind]
            )
        except KeyError as exc:
            raise TypeError(f"Unsupported Java return type: {return_type}") from exc

    # Field Operations
    def GetFieldID(self, clazz: Any, name: str, signature: str) -> Optional[Any]:
        """Get field ID"""
        if not clazz:
            raise ValueError("clazz must not be NULL")
        func = self._get_function(
            JNIFunctionIndices.GetFieldID, JNIPrototypes.GetFieldID
        )
        result = func(self.env, clazz, name.encode("utf-8"), signature.encode("utf-8"))
        self._check_exception()
        return result

    def GetObjectField(self, obj: Any, field_id: Any) -> Optional[Any]:
        """Get object field"""
        func = self._get_function(
            JNIFunctionIndices.GetObjectField, JNIPrototypes.GetObjectField
        )
        return func(self.env, obj, field_id)

    def GetTypedField(self, obj: Any, field_id: Any, field_type: str) -> Any:
        """Read an instance field using its reflected type."""
        return self._get_typed_field(False, obj, field_id, field_type)

    def GetTypedStaticField(self, clazz: Any, field_id: Any, field_type: str) -> Any:
        """Read a static field using its reflected type."""
        return self._get_typed_field(True, clazz, field_id, field_type)

    def _get_typed_field(
        self, is_static: bool, target: Any, field_id: Any, field_type: str
    ) -> Any:
        if not target or not field_id:
            raise ValueError("target and field_id must not be NULL")
        kind = field_type if field_type in _PRIMITIVE_JAVA_TYPES else "object"
        getter_map = (
            _TYPED_STATIC_FIELD_GETTERS if is_static else _TYPED_INSTANCE_FIELD_GETTERS
        )
        index, prototype = getter_map[kind]
        func = self._get_function(index, prototype)
        result = func(self.env, target, field_id)
        self._check_exception()
        return result

    def SetObjectField(self, obj: Any, field_id: Any, value: Any) -> None:
        """Set object field"""
        func = self._get_function(
            JNIFunctionIndices.SetObjectField, JNIPrototypes.SetObjectField
        )
        func(self.env, obj, field_id, value)

    def GetStaticFieldID(self, clazz: Any, name: str, signature: str) -> Optional[Any]:
        """Get static field ID"""
        if not clazz:
            raise ValueError("clazz must not be NULL")
        func = self._get_function(
            JNIFunctionIndices.GetStaticFieldID, JNIPrototypes.GetStaticFieldID
        )
        result = func(self.env, clazz, name.encode("utf-8"), signature.encode("utf-8"))
        self._check_exception()
        return result

    def GetStaticObjectField(self, clazz: Any, field_id: Any) -> Optional[Any]:
        """Get static object field"""
        if not clazz:
            raise ValueError("clazz must not be NULL")
        if not field_id:
            raise ValueError("field_id must not be NULL")
        func = self._get_function(
            JNIFunctionIndices.GetStaticObjectField, JNIPrototypes.GetStaticObjectField
        )
        result = func(self.env, clazz, field_id)
        self._check_exception()
        return result

    def SetStaticObjectField(self, clazz: Any, field_id: Any, value: Any) -> None:
        """Set static object field"""
        func = self._get_function(
            JNIFunctionIndices.SetStaticObjectField, JNIPrototypes.SetStaticObjectField
        )
        func(self.env, clazz, field_id, value)

    # String Operations
    def NewString(self, unicode_chars: Any, length: int) -> Optional[Any]:
        """Create new string from unicode characters"""
        func = self._get_function(JNIFunctionIndices.NewString, JNIPrototypes.NewString)
        return func(self.env, unicode_chars, length)

    def GetStringLength(self, string: Any) -> int:
        """Get string length"""
        func = self._get_function(
            JNIFunctionIndices.GetStringLength, JNIPrototypes.GetStringLength
        )
        return cast(int, func(self.env, string))

    def GetStringChars(
        self, string: Any, is_copy: Optional[Any] = None
    ) -> Optional[Any]:
        """Get string characters"""
        func = self._get_function(
            JNIFunctionIndices.GetStringChars, JNIPrototypes.GetStringChars
        )
        return func(self.env, string, is_copy)

    def ReleaseStringChars(self, string: Any, chars: Any) -> None:
        """Release string characters"""
        func = self._get_function(
            JNIFunctionIndices.ReleaseStringChars, JNIPrototypes.ReleaseStringChars
        )
        func(self.env, string, chars)

    def NewStringUTF(self, utf_chars: str) -> Optional[Any]:
        """UTF-8文字列から新しい文字列を作成"""
        func = self._get_function(
            JNIFunctionIndices.NewStringUTF, JNIPrototypes.NewStringUTF
        )
        result = func(self.env, utf_chars.encode("utf-8"))
        self._check_exception()
        return result

    def GetStringUTFLength(self, string: Any) -> int:
        """Get UTF-8 string length"""
        func = self._get_function(
            JNIFunctionIndices.GetStringUTFLength, JNIPrototypes.GetStringUTFLength
        )
        return cast(int, func(self.env, string))

    def GetStringUTFChars(
        self, string: Any, is_copy: Optional[Any] = None
    ) -> Optional[str]:
        """Get UTF-8 string characters"""
        if not string:
            return None
        func = self._get_function(
            JNIFunctionIndices.GetStringUTFChars, JNIPrototypes.GetStringUTFChars
        )
        char_ptr = func(self.env, string, is_copy)
        self._check_exception()
        if char_ptr:
            try:
                import ctypes

                # JNI GetStringUTFChars returns a pointer to null-terminated UTF-8 string
                # Use string_at to read the entire null-terminated string
                result_bytes = ctypes.string_at(char_ptr)
                return result_bytes.decode("utf-8")
            except (UnicodeDecodeError, AttributeError, TypeError):
                return None
        return None

    def ReleaseStringUTFChars(self, string: Any, utf_chars: Any) -> None:
        """Release UTF-8 string characters"""
        func = self._get_function(
            JNIFunctionIndices.ReleaseStringUTFChars,
            JNIPrototypes.ReleaseStringUTFChars,
        )
        func(self.env, string, utf_chars)

    # Array Operations
    def GetArrayLength(self, array: Any) -> int:
        """Get array length"""
        func = self._get_function(
            JNIFunctionIndices.GetArrayLength, JNIPrototypes.GetArrayLength
        )
        return cast(int, func(self.env, array))

    def NewObjectArray(
        self, length: int, element_class: Any, initial_element: Any
    ) -> Optional[Any]:
        """Create new object array"""
        func = self._get_function(
            JNIFunctionIndices.NewObjectArray, JNIPrototypes.NewObjectArray
        )
        return func(self.env, length, element_class, initial_element)

    def GetObjectArrayElement(self, array: Any, index: int) -> Optional[Any]:
        """Get object array element"""
        func = self._get_function(
            JNIFunctionIndices.GetObjectArrayElement,
            JNIPrototypes.GetObjectArrayElement,
        )
        return func(self.env, array, index)

    def SetObjectArrayElement(self, array: Any, index: int, value: Any) -> None:
        """Set object array element"""
        func = self._get_function(
            JNIFunctionIndices.SetObjectArrayElement,
            JNIPrototypes.SetObjectArrayElement,
        )
        func(self.env, array, index, value)

    def NewTypedArray(self, java_type: str, values: list[Any] | tuple[Any, ...]) -> Any:
        """Create a one- or multi-dimensional Java array from Python values."""
        descriptor = java_type_to_descriptor(java_type)
        if not descriptor.startswith("["):
            raise TypeError(f"Not a Java array type: {java_type}")

        component_type = array_component_type(descriptor)
        if component_type in _PRIMITIVE_JAVA_TYPES:
            return self._new_primitive_array(component_type, values)

        component_descriptor = descriptor[1:]
        if component_descriptor.startswith("["):
            element_class_name = component_descriptor
        else:
            element_class_name = component_descriptor[1:-1]
        element_class = self.FindClass(element_class_name)
        if not element_class:
            raise RuntimeError(f"Could not find array element class {component_type}")

        result = self.NewObjectArray(len(values), element_class, None)
        if not result:
            raise RuntimeError(f"Failed to allocate Java array {descriptor}")
        for index, value in enumerate(values):
            if component_descriptor.startswith("["):
                converted = self.NewTypedArray(component_descriptor, value)
            else:
                converted = self._prepare_reference_argument(value, component_type)
            self.SetObjectArrayElement(result, index, converted)
        self._check_exception()
        return result

    def _new_primitive_array(
        self, primitive_type: str, values: list[Any] | tuple[Any, ...]
    ) -> Any:
        for value in values:
            self._validate_primitive_argument(value, primitive_type)

        (
            ctype,
            new_index,
            new_prototype,
            _,
            _,
            set_index,
            set_prototype,
        ) = _PRIMITIVE_ARRAY_OPERATIONS[primitive_type]
        new_func = self._get_function(new_index, new_prototype)
        result = new_func(self.env, len(values))
        if not result:
            self._check_exception()
            raise RuntimeError(f"Failed to allocate Java {primitive_type} array")

        converted_values = [
            ord(value) if primitive_type == "char" and isinstance(value, str) else value
            for value in values
        ]
        buffer = (ctype * len(converted_values))(*converted_values)
        set_func = self._get_function(set_index, set_prototype)
        set_func(self.env, result, 0, len(converted_values), buffer)
        self._check_exception()
        return result

    def GetTypedArrayElements(self, array: Any, java_type: str) -> list[Any]:
        """Read Java array elements, leaving object conversion to the caller."""
        if not array:
            return []
        component_type = array_component_type(java_type)
        length = self.GetArrayLength(array)
        if component_type not in _PRIMITIVE_JAVA_TYPES:
            return [self.GetObjectArrayElement(array, index) for index in range(length)]

        (
            ctype,
            _,
            _,
            get_index,
            get_prototype,
            _,
            _,
        ) = _PRIMITIVE_ARRAY_OPERATIONS[component_type]
        buffer = (ctype * length)()
        get_func = self._get_function(get_index, get_prototype)
        get_func(self.env, array, 0, length, buffer)
        self._check_exception()
        return list(buffer)

    # Exception Operations
    def Throw(self, throwable: Any) -> int:
        """Throw exception"""
        func = self._get_function(JNIFunctionIndices.Throw, JNIPrototypes.Throw)
        return cast(int, func(self.env, throwable))

    def ThrowNew(self, clazz: Any, message: str) -> int:
        """Throw new exception"""
        func = self._get_function(JNIFunctionIndices.ThrowNew, JNIPrototypes.ThrowNew)
        return cast(int, func(self.env, clazz, message.encode("utf-8")))

    def ExceptionOccurred(self) -> Optional[Any]:
        """Check if exception occurred"""
        func = self._get_function(
            JNIFunctionIndices.ExceptionOccurred, JNIPrototypes.ExceptionOccurred
        )
        return func(self.env)

    def ExceptionDescribe(self) -> None:
        """Describe exception"""
        func = self._get_function(
            JNIFunctionIndices.ExceptionDescribe, JNIPrototypes.ExceptionDescribe
        )
        func(self.env)

    def ExceptionClear(self) -> None:
        """Clear exception"""
        func = self._get_function(
            JNIFunctionIndices.ExceptionClear, JNIPrototypes.ExceptionClear
        )
        func(self.env)

    def FatalError(self, message: str) -> None:
        """Report fatal error"""
        func = self._get_function(
            JNIFunctionIndices.FatalError, JNIPrototypes.FatalError
        )
        func(self.env, message.encode("utf-8"))

    def ExceptionCheck(self) -> bool:
        """Check if exception is pending"""
        func = self._get_function(
            JNIFunctionIndices.ExceptionCheck, JNIPrototypes.ExceptionCheck
        )
        return bool(func(self.env))

    # Reference Management
    def NewGlobalRef(self, obj: Any) -> Optional[Any]:
        """グローバル参照を作成"""
        func = self._get_function(
            JNIFunctionIndices.NewGlobalRef, JNIPrototypes.NewGlobalRef
        )
        return func(self.env, obj)

    def DeleteGlobalRef(self, global_ref: Any) -> None:
        """Delete global reference"""
        func = self._get_function(
            JNIFunctionIndices.DeleteGlobalRef, JNIPrototypes.DeleteGlobalRef
        )
        func(self.env, global_ref)

    def DeleteLocalRef(self, local_ref: Any) -> None:
        """Delete local reference"""
        func = self._get_function(
            JNIFunctionIndices.DeleteLocalRef, JNIPrototypes.DeleteLocalRef
        )
        func(self.env, local_ref)

    def NewLocalRef(self, ref: Any) -> Optional[Any]:
        """Create local reference"""
        func = self._get_function(
            JNIFunctionIndices.NewLocalRef, JNIPrototypes.NewLocalRef
        )
        return func(self.env, ref)

    def EnsureLocalCapacity(self, capacity: int) -> int:
        """Ensure local reference capacity"""
        func = self._get_function(
            JNIFunctionIndices.EnsureLocalCapacity, JNIPrototypes.EnsureLocalCapacity
        )
        return cast(int, func(self.env, capacity))

    def PushLocalFrame(self, capacity: int) -> int:
        """Push local frame"""
        func = self._get_function(
            JNIFunctionIndices.PushLocalFrame, JNIPrototypes.PushLocalFrame
        )
        return cast(int, func(self.env, capacity))

    def PopLocalFrame(self, result: Any) -> Optional[Any]:
        """Pop local frame"""
        func = self._get_function(
            JNIFunctionIndices.PopLocalFrame, JNIPrototypes.PopLocalFrame
        )
        return func(self.env, result)

    # Weak Global References
    def NewWeakGlobalRef(self, obj: Any) -> Optional[Any]:
        """Create weak global reference"""
        func = self._get_function(
            JNIFunctionIndices.NewWeakGlobalRef, JNIPrototypes.NewWeakGlobalRef
        )
        return func(self.env, obj)

    def DeleteWeakGlobalRef(self, weak_ref: Any) -> None:
        """Delete weak global reference"""
        func = self._get_function(
            JNIFunctionIndices.DeleteWeakGlobalRef, JNIPrototypes.DeleteWeakGlobalRef
        )
        func(self.env, weak_ref)

    # Monitor Operations
    def MonitorEnter(self, obj: Any) -> int:
        """Enter monitor"""
        func = self._get_function(
            JNIFunctionIndices.MonitorEnter, JNIPrototypes.MonitorEnter
        )
        return cast(int, func(self.env, obj))

    def MonitorExit(self, obj: Any) -> int:
        """Exit monitor"""
        func = self._get_function(
            JNIFunctionIndices.MonitorExit, JNIPrototypes.MonitorExit
        )
        return cast(int, func(self.env, obj))

    # Java VM Interface
    def GetJavaVM(self, vm_ptr: Any) -> int:
        """Get Java VM interface"""
        func = self._get_function(JNIFunctionIndices.GetJavaVM, JNIPrototypes.GetJavaVM)
        return cast(int, func(self.env, vm_ptr))

    # Reflection Support
    def FromReflectedMethod(self, method: Any) -> Optional[Any]:
        """Convert reflected method to method ID"""
        func = self._get_function(
            JNIFunctionIndices.FromReflectedMethod, JNIPrototypes.FromReflectedMethod
        )
        result = func(self.env, method)
        self._check_exception()
        return result

    def FromReflectedField(self, field: Any) -> Optional[Any]:
        """Convert reflected field to field ID"""
        func = self._get_function(
            JNIFunctionIndices.FromReflectedField, JNIPrototypes.FromReflectedField
        )
        result = func(self.env, field)
        self._check_exception()
        return result

    def ToReflectedMethod(
        self, clazz: Any, method_id: Any, is_static: bool
    ) -> Optional[Any]:
        """Convert method ID to reflected method"""
        func = self._get_function(
            JNIFunctionIndices.ToReflectedMethod, JNIPrototypes.ToReflectedMethod
        )
        return func(self.env, clazz, method_id, is_static)

    def ToReflectedField(
        self, clazz: Any, field_id: Any, is_static: bool
    ) -> Optional[Any]:
        """Convert field ID to reflected field"""
        func = self._get_function(
            JNIFunctionIndices.ToReflectedField, JNIPrototypes.ToReflectedField
        )
        return func(self.env, clazz, field_id, is_static)
