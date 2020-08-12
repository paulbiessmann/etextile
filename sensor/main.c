/*
 * Copyright (C) 2020 Freie Universität Berlin
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

#include <stdio.h>
#include <stdint.h>

#include "assert.h"
#include "event/timeout.h"
#include "nimble_riot.h"
#include "net/bluetil/ad.h"

#include "host/ble_hs.h"
#include "host/ble_gatt.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

#define BLE_GATT_SVC_ETEXTILE   (20000)
#define BLE_GATT_CHAR_ETEXTILE_SENSOR_MEASURE (BLE_GATT_SVC_ETEXTILE + 1)

#define SENSOR_LOCATION         (0x02)      /* wrist sensor */
#define UPDATE_INTERVAL         (100U * US_PER_MS)
#define BAT_LEVEL               (42U)

static const char *_device_name = "RIOT eTextile Sensor";
static const char *_manufacturer_name = "riot-os.org";
static const char *_model_number = "2A";
static const char *_serial_number = "a8b302c7f3-29183-x8";
static const char *_fw_ver = "0.0.0";
static const char *_hw_ver = "0.0.0";

static struct __attribute__((packed)) {
    uint16_t value;
    uint16_t values[15];
    uint16_t values2[16];
} _etextile_data = { 0 };

static event_queue_t _eq;
static event_t _update_evt;
static event_timeout_t _update_timeout_evt;

static uint16_t _conn_handle;
static uint16_t _etextile_val_handle;

static int _etextile_handler(uint16_t conn_handle, uint16_t attr_handle,
                        struct ble_gatt_access_ctxt *ctxt, void *arg);

static int _devinfo_handler(uint16_t conn_handle, uint16_t attr_handle,
                            struct ble_gatt_access_ctxt *ctxt, void *arg);

static int _bas_handler(uint16_t conn_handle, uint16_t attr_handle,
                        struct ble_gatt_access_ctxt *ctxt, void *arg);

static void _start_advertising(void);
static void _start_updating(void);
static void _stop_updating(void);

/* GATT service definitions */
static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
    {
        /* Heart Rate Service */
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(BLE_GATT_SVC_ETEXTILE),
        .characteristics = (struct ble_gatt_chr_def[]) { {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_ETEXTILE_SENSOR_MEASURE),
            .access_cb = _etextile_handler,
            .val_handle = &_etextile_val_handle,
            .flags = BLE_GATT_CHR_F_NOTIFY,
        }, {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_BODY_SENSE_LOC),
            .access_cb = _etextile_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            0, /* no more characteristics in this service */
        }, }
    },
    {
        /* Device Information Service */
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(BLE_GATT_SVC_DEVINFO),
        .characteristics = (struct ble_gatt_chr_def[]) { {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_MANUFACTURER_NAME),
            .access_cb = _devinfo_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_MODEL_NUMBER_STR),
            .access_cb = _devinfo_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_SERIAL_NUMBER_STR),
            .access_cb = _devinfo_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_FW_REV_STR),
            .access_cb = _devinfo_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_HW_REV_STR),
            .access_cb = _devinfo_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            0, /* no more characteristics in this service */
        }, }
    },
    {
        /* Battery Level Service */
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(BLE_GATT_SVC_BAS),
        .characteristics = (struct ble_gatt_chr_def[]) { {
            .uuid = BLE_UUID16_DECLARE(BLE_GATT_CHAR_BATTERY_LEVEL),
            .access_cb = _bas_handler,
            .flags = BLE_GATT_CHR_F_READ,
        }, {
            0, /* no more characteristics in this service */
        }, }
    },
    {
        0, /* no more services */
    },
};

static int _etextile_handler(uint16_t conn_handle, uint16_t attr_handle,
                        struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn_handle;
    (void)attr_handle;
    (void)arg;

    if (ble_uuid_u16(ctxt->chr->uuid) != BLE_GATT_CHAR_BODY_SENSE_LOC) {
        return BLE_ATT_ERR_UNLIKELY;
    }

    puts("[READ] etextile sensor service: body sensor location value");

    uint8_t loc = SENSOR_LOCATION;
    int res = os_mbuf_append(ctxt->om, &loc, sizeof(loc));
    return (res == 0) ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}

static int _devinfo_handler(uint16_t conn_handle, uint16_t attr_handle,
                            struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn_handle;
    (void)attr_handle;
    (void)arg;
    const char *str;

    switch (ble_uuid_u16(ctxt->chr->uuid)) {
        case BLE_GATT_CHAR_MANUFACTURER_NAME:
            puts("[READ] device information service: manufacturer name value");
            str = _manufacturer_name;
            break;
        case BLE_GATT_CHAR_MODEL_NUMBER_STR:
            puts("[READ] device information service: model number value");
            str = _model_number;
            break;
        case BLE_GATT_CHAR_SERIAL_NUMBER_STR:
            puts("[READ] device information service: serial number value");
            str = _serial_number;
            break;
        case BLE_GATT_CHAR_FW_REV_STR:
            puts("[READ] device information service: firmware revision value");
            str = _fw_ver;
            break;
        case BLE_GATT_CHAR_HW_REV_STR:
            puts("[READ] device information service: hardware revision value");
            str = _hw_ver;
            break;
        default:
            return BLE_ATT_ERR_UNLIKELY;
    }

    int res = os_mbuf_append(ctxt->om, str, strlen(str));
    return (res == 0) ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}

static int _bas_handler(uint16_t conn_handle, uint16_t attr_handle,
                        struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn_handle;
    (void)attr_handle;
    (void)arg;

    puts("[READ] battery level service: battery level value");

    uint8_t level = BAT_LEVEL;  /* this battery will never drain :-) */
    int res = os_mbuf_append(ctxt->om, &level, sizeof(level));
    return (res == 0) ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}

static int gap_event_cb(struct ble_gap_event *event, void *arg)
{
    (void)arg;

    switch (event->type) {
        case BLE_GAP_EVENT_CONNECT:
            if (event->connect.status) {
                _stop_updating();
                _start_advertising();
                return 0;
            }
            _conn_handle = event->connect.conn_handle;
            break;

        case BLE_GAP_EVENT_DISCONNECT:
            _stop_updating();
            _start_advertising();
            break;

        case BLE_GAP_EVENT_SUBSCRIBE:
            if (event->subscribe.attr_handle == _etextile_val_handle) {
                if (event->subscribe.cur_notify == 1) {
                    _start_updating();
                }
                else {
                    _stop_updating();
                }
            }
            break;
    }

    return 0;
}

static void _start_advertising(void)
{
    struct ble_gap_adv_params advp;
    int res;

    memset(&advp, 0, sizeof advp);
    advp.conn_mode = BLE_GAP_CONN_MODE_UND;
    advp.disc_mode = BLE_GAP_DISC_MODE_GEN;
    advp.itvl_min  = BLE_GAP_ADV_FAST_INTERVAL1_MIN;
    advp.itvl_max  = BLE_GAP_ADV_FAST_INTERVAL1_MAX;
    res = ble_gap_adv_start(nimble_riot_own_addr_type, NULL, BLE_HS_FOREVER,
                            &advp, gap_event_cb, NULL);
    assert(res == 0);
    (void)res;
}

static void _start_updating(void)
{
    event_timeout_set(&_update_timeout_evt, UPDATE_INTERVAL);
    puts("[NOTIFY_ENABLED] etextile sensor service");
}

static void _stop_updating(void)
{
    event_timeout_clear(&_update_timeout_evt);
    puts("[NOTIFY_DISABLED] etextile sensor service");
}

static void _sensor_update(event_t *e)
{
    (void)e;
    struct os_mbuf *om;

    _etextile_data.value++;

    printf("[NOTIFY] etextile sensor service: measurement %i\n", (int)_etextile_data.value);

    /* send etextile sensor data notification to GATT client */
    om = ble_hs_mbuf_from_flat(&_etextile_data, sizeof(_etextile_data));
    if (om) {
        int res = ble_gattc_notify_custom(_conn_handle, _etextile_val_handle, om);
        if (res != 0) {
            printf("ble_gattc_notify_custom() res=%i\n", res);
        }
    } else {
        printf("ble_hs_mbuf_from_flat() allocation failed\n");
    }

    /* schedule next update event */
    event_timeout_set(&_update_timeout_evt, UPDATE_INTERVAL);
}

int main(void)
{
    puts("RIOT eTextile sensor");

    int res = 0;
    (void)res;

    /* setup local event queue (for handling etextile sensor updates) */
    event_queue_init(&_eq);
    _update_evt.handler = _sensor_update;
    event_timeout_init(&_update_timeout_evt, &_eq, &_update_evt);

    /* verify and add our custom services */
    res = ble_gatts_count_cfg(gatt_svr_svcs);
    assert(res == 0);
    res = ble_gatts_add_svcs(gatt_svr_svcs);
    assert(res == 0);

    /* set the device name */
    ble_svc_gap_device_name_set(_device_name);
    /* reload the GATT server to link our added services */
    ble_gatts_start();

    /* configure and set the advertising data */
    uint8_t buf[BLE_HS_ADV_MAX_SZ];
    bluetil_ad_t ad;
    bluetil_ad_init_with_flags(&ad, buf, sizeof(buf), BLUETIL_AD_FLAGS_DEFAULT);
    uint16_t etextile_uuid = BLE_GATT_SVC_HRS;
    bluetil_ad_add(&ad, BLE_GAP_AD_UUID16_INCOMP, &etextile_uuid, sizeof(etextile_uuid));
    bluetil_ad_add_name(&ad, _device_name);
    ble_gap_adv_set_data(ad.buf, ad.pos);

    /* start to advertise this node */
    _start_advertising();

    /* run an event loop for handling the etextile sensor update events */
    event_loop(&_eq);

    return 0;
}
